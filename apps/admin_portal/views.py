from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.content.models import GenerationProfile, Genre, Option, Question, Scenario, Tag

from .forms import ForcePasswordResetForm, QuestionWizardForm
from .models import AuditLog
from .services.question_wizard_service import generate_and_persist_options, retry_option_generation


User = get_user_model()


def _question_is_publishable(question):
    options = list(question.options.select_related("llm_model"))
    if len(options) != question.choice_count:
        return False
    human_options = [option for option in options if option.author_type == Option.AuthorType.HUMAN]
    ai_options = [option for option in options if option.author_type == Option.AuthorType.AI]
    if len(human_options) != 1:
        return False
    if len(ai_options) != question.choice_count - 1:
        return False
    if any(option.generation_status != Option.GenerationStatus.OK for option in options):
        return False
    if question.choice_count == 4 and len({option.llm_model_id for option in ai_options}) != 3:
        return False
    return True


def _write_audit(*, actor, event_type, target_user=None, target_question=None, metadata=None):
    AuditLog.objects.create(
        actor=actor,
        event_type=event_type,
        target_user=target_user,
        target_question=target_question,
        metadata_json=metadata or {},
    )


@staff_member_required
def admin_dashboard_view(request):
    published_count = Question.objects.filter(status=Question.Status.PUBLISHED).count()
    draft_count = Question.objects.filter(status=Question.Status.DRAFT).count()
    stock_by_difficulty = (
        Question.objects.filter(status=Question.Status.PUBLISHED)
        .values("difficulty", "choice_count")
        .annotate(count=Count("id"))
        .order_by("difficulty", "choice_count")
    )
    return render(
        request,
        "admin_portal/dashboard.html",
        {
            "published_count": published_count,
            "draft_count": draft_count,
            "stock_by_difficulty": stock_by_difficulty,
        },
    )


@staff_member_required
@transaction.atomic
def question_create_view(request):
    form = QuestionWizardForm(request.POST or None)
    context = {
        "form": form,
        "genres": Genre.objects.filter(is_active=True).order_by("name"),
        "tags": Tag.objects.filter(is_active=True).order_by("name"),
        "profiles": GenerationProfile.objects.order_by("name"),
    }
    if request.method == "POST" and form.is_valid():
        genre = get_object_or_404(Genre, id=form.cleaned_data["genre_id"], is_active=True)
        scenario = Scenario.objects.create(
            user_message_text=form.cleaned_data["user_message_text"],
            human_reply_text=form.cleaned_data["human_reply_text"],
            genre=genre,
            created_by_admin=request.user,
        )
        tag_ids_raw = form.cleaned_data.get("tag_ids", "").strip()
        if tag_ids_raw:
            tag_ids = [int(value.strip()) for value in tag_ids_raw.split(",") if value.strip().isdigit()]
            scenario.tags.add(*Tag.objects.filter(id__in=tag_ids, is_active=True))

        profile = None
        if form.cleaned_data.get("generation_profile_id"):
            profile = GenerationProfile.objects.filter(
                id=form.cleaned_data["generation_profile_id"]
            ).first()

        question = Question.objects.create(
            scenario=scenario,
            status=Question.Status.DRAFT,
            difficulty=form.cleaned_data["difficulty"],
            choice_count=form.cleaned_data["choice_count"],
            generation_profile=profile,
            created_by_admin=request.user,
        )
        generate_and_persist_options(
            question=question,
            selected_model_ids=form.cleaned_data["selected_model_ids"],
            system_prompt=form.cleaned_data.get("system_prompt", ""),
            temperature=form.cleaned_data.get("temperature"),
            seed=form.cleaned_data.get("seed"),
            max_tokens=form.cleaned_data.get("max_tokens"),
        )
        if form.cleaned_data.get("publish_now") and _question_is_publishable(question):
            question.status = Question.Status.PUBLISHED
            question.published_at = question.published_at or question.created_at
            question.save(update_fields=["status", "published_at", "updated_at"])
            _write_audit(
                actor=request.user,
                event_type=AuditLog.EventType.QUESTION_PUBLISH,
                target_question=question,
            )
        elif form.cleaned_data.get("publish_now"):
            messages.warning(request, "公開条件を満たさなかったため下書き保存しました。")
        messages.success(request, f"Question #{question.id} を作成しました。")
        return redirect("admin-question-list")
    return render(request, "admin_portal/question_create.html", context)


@staff_member_required
def question_list_view(request):
    questions = Question.objects.select_related("scenario", "scenario__genre").prefetch_related("options").order_by("-id")
    status = request.GET.get("status")
    difficulty = request.GET.get("difficulty")
    if status:
        questions = questions.filter(status=status)
    if difficulty:
        questions = questions.filter(difficulty=difficulty)

    if request.method == "POST":
        question = get_object_or_404(Question, id=request.POST.get("question_id"))
        action = request.POST.get("action")
        if action == "publish":
            if _question_is_publishable(question):
                question.status = Question.Status.PUBLISHED
                question.published_at = question.published_at or question.created_at
                question.save(update_fields=["status", "published_at", "updated_at"])
                _write_audit(
                    actor=request.user,
                    event_type=AuditLog.EventType.QUESTION_PUBLISH,
                    target_question=question,
                )
            else:
                messages.error(request, "公開条件を満たしていません。")
        elif action == "archive":
            question.status = Question.Status.ARCHIVED
            question.save(update_fields=["status", "updated_at"])
            _write_audit(
                actor=request.user,
                event_type=AuditLog.EventType.QUESTION_ARCHIVE,
                target_question=question,
            )
        elif action == "variant":
            Question.objects.create(
                scenario=question.scenario,
                status=Question.Status.DRAFT,
                difficulty=question.difficulty,
                choice_count=question.choice_count,
                generation_profile=question.generation_profile,
                variant_of_question=question,
                created_by_admin=request.user,
            )
        messages.success(request, "操作を反映しました。")
        return redirect("admin-question-list")

    stats = (
        Question.objects.values("id")
        .annotate(
            phase1_total=Count("session_questions", filter=Q(session_questions__phase1_is_correct__isnull=False)),
            phase1_correct=Count("session_questions", filter=Q(session_questions__phase1_is_correct=True)),
            phase2_points=Count("session_questions__phase2_score"),
        )
    )
    stats_by_id = {row["id"]: row for row in stats}
    return render(
        request,
        "admin_portal/question_list.html",
        {"questions": questions, "stats_by_id": stats_by_id},
    )


@staff_member_required
def option_retry_view(request, option_id):
    option = get_object_or_404(Option, id=option_id, author_type=Option.AuthorType.AI)
    retry_option_generation(option)
    messages.info(request, f"Option #{option.id} の再試行を実行しました。")
    return redirect("admin-question-list")


@staff_member_required
def user_list_view(request):
    users = User.objects.order_by("-id")
    reset_form = ForcePasswordResetForm()
    return render(
        request,
        "admin_portal/user_list.html",
        {"users": users, "reset_form": reset_form},
    )


@staff_member_required
def force_password_reset_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    form = ForcePasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        target_user.set_password(form.cleaned_data["new_password"])
        target_user.save(update_fields=["password"])
        _write_audit(
            actor=request.user,
            event_type=AuditLog.EventType.USER_PASSWORD_RESET,
            target_user=target_user,
        )
        messages.success(request, f"{target_user.login_id} のパスワードを更新しました。")
    return redirect("admin-user-list")

# Create your views here.
