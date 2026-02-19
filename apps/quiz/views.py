from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.content.models import Option
from apps.quiz.forms import Phase1Form, Phase2Form, QuizStartForm
from apps.quiz.models import QuizSession, SessionQuestion
from apps.quiz.services.answer_service import submit_phase1, submit_phase2
from apps.quiz.services.session_allocator import start_or_resume_session


def _build_letter_option_map(session_question):
    option_map = {}
    options = {
        option.id: option
        for option in session_question.question.options.select_related("llm_model")
    }
    for letter, option_id in session_question.shuffle_map_json.items():
        option_map[letter] = options.get(option_id)
    return option_map


def _next_url_for_session_question(session, current_index):
    has_next = session.session_questions.filter(order_index=current_index + 1).exists()
    if has_next:
        return reverse(
            "quiz-question",
            kwargs={"session_id": session.id, "index": current_index + 1},
        )
    return reverse("quiz-session-result", kwargs={"session_id": session.id})


def _session_phase1_stats(session):
    answered = session.session_questions.exclude(phase1_is_correct__isnull=True)
    total = answered.count()
    correct = answered.filter(phase1_is_correct=True).count()
    rate = (correct / total * 100) if total else 0
    streak = 0
    best_streak = 0
    for item in answered.order_by("order_index"):
        if item.phase1_is_correct:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0
    return {"total": total, "correct": correct, "rate": rate, "streak": streak, "best_streak": best_streak}


@login_required
def quiz_start_view(request):
    form = QuizStartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        restart = request.POST.get("restart") == "1"
        allocation = start_or_resume_session(
            user=request.user,
            difficulty=form.cleaned_data["difficulty"],
            choice_count=form.cleaned_data["choice_count"],
            num_questions_requested=form.cleaned_data["num_questions"],
            restart=restart,
        )
        if allocation["out_of_stock"]:
            return redirect(
                f"{reverse('quiz-out-of-stock')}?difficulty={form.cleaned_data['difficulty']}&"
                f"choice_count={form.cleaned_data['choice_count']}&"
                f"num_questions={form.cleaned_data['num_questions']}&"
                f"available_count={allocation['available_count']}"
            )
        return redirect("quiz-question", session_id=allocation["session"].id, index=0)
    return render(request, "quiz/start.html", {"form": form})


@login_required
def quiz_out_of_stock_view(request):
    context = {
        "difficulty": request.GET.get("difficulty"),
        "choice_count": request.GET.get("choice_count"),
        "num_questions": request.GET.get("num_questions"),
        "available_count": int(request.GET.get("available_count", 0)),
    }
    if request.method == "POST" and context["available_count"] > 0:
        allocation = start_or_resume_session(
            user=request.user,
            difficulty=request.POST["difficulty"],
            choice_count=int(request.POST["choice_count"]),
            num_questions_requested=int(request.POST["num_questions"]),
            force_num_questions=int(request.POST["available_count"]),
            restart=True,
        )
        if not allocation["out_of_stock"]:
            return redirect("quiz-question", session_id=allocation["session"].id, index=0)
    return render(request, "quiz/out_of_stock.html", context)


@login_required
def quiz_question_view(request, session_id, index):
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    session_question = get_object_or_404(SessionQuestion, session=session, order_index=index)
    if session_question.phase1_answered_at:
        return redirect("quiz-phase1-result", session_id=session.id, index=index)

    letter_option_map = _build_letter_option_map(session_question)
    form = Phase1Form(
        request.POST or None,
        available_letters=list(letter_option_map.keys()),
    )
    if request.method == "POST" and form.is_valid():
        submit_phase1(
            session_question=session_question,
            selected_letter=form.cleaned_data["selected_letter"],
            phase1_time_ms=form.cleaned_data.get("phase1_time_ms"),
        )
        return redirect("quiz-phase1-result", session_id=session.id, index=index)
    return render(
        request,
        "quiz/question.html",
        {
            "session": session,
            "session_question": session_question,
            "scenario": session_question.question.scenario,
            "letter_option_map": letter_option_map,
            "form": form,
        },
    )


@login_required
def quiz_phase1_result_view(request, session_id, index):
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    session_question = get_object_or_404(SessionQuestion, session=session, order_index=index)
    if not session_question.phase1_answered_at:
        return redirect("quiz-question", session_id=session.id, index=index)
    stats = _session_phase1_stats(session)
    letter_option_map = _build_letter_option_map(session_question)
    human_option_id = session_question.question.options.get(
        author_type=Option.AuthorType.HUMAN
    ).id
    human_letter = None
    for letter, option in letter_option_map.items():
        if option and option.id == human_option_id:
            human_letter = letter
            break
    if session.choice_count == 4:
        next_url = reverse("quiz-phase2", kwargs={"session_id": session.id, "index": index})
    else:
        next_url = _next_url_for_session_question(session, index)
    return render(
        request,
        "quiz/phase1_result.html",
        {
            "session": session,
            "session_question": session_question,
            "stats": stats,
            "human_letter": human_letter if session.choice_count == 2 else None,
            "next_url": next_url,
        },
    )


@login_required
def quiz_phase2_view(request, session_id, index):
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    session_question = get_object_or_404(SessionQuestion, session=session, order_index=index)
    if session.choice_count != 4:
        return redirect(_next_url_for_session_question(session, index))
    if not session_question.phase1_answered_at:
        return redirect("quiz-question", session_id=session.id, index=index)
    if session_question.phase2_answered_at:
        return redirect("quiz-phase2-result", session_id=session.id, index=index)

    question = session_question.question
    human_option = question.options.get(author_type=Option.AuthorType.HUMAN)
    ai_options = list(
        question.options.filter(author_type=Option.AuthorType.AI).select_related("llm_model")
    )
    group_choices = sorted(
        {(option.llm_model.display_group_slug, option.llm_model.display_group) for option in ai_options},
        key=lambda item: item[0],
    )
    form = Phase2Form(request.POST or None, ai_options=ai_options, group_choices=group_choices)
    error = None
    if request.method == "POST" and form.is_valid():
        assignment_map = {str(option.id): form.cleaned_data[f"option_{option.id}"] for option in ai_options}
        if len(set(assignment_map.values())) != len(assignment_map.values()):
            error = "同じモデル系統は1回のみ選択できます。"
        else:
            submit_phase2(
                session_question=session_question,
                assignment_map=assignment_map,
                phase2_time_ms=form.cleaned_data.get("phase2_time_ms"),
            )
            return redirect("quiz-phase2-result", session_id=session.id, index=index)
    letter_option_map = _build_letter_option_map(session_question)
    phase2_rows = []
    for letter, option in letter_option_map.items():
        phase2_rows.append(
            {
                "letter": letter,
                "option": option,
                "is_human": option.id == human_option.id,
                "field": form[f"option_{option.id}"] if option.id != human_option.id else None,
            }
        )
    return render(
        request,
        "quiz/phase2.html",
        {
            "session": session,
            "session_question": session_question,
            "human_option_id": human_option.id,
            "phase2_rows": phase2_rows,
            "ai_options": ai_options,
            "form": form,
            "group_choices": group_choices,
            "error": error,
        },
    )


@login_required
def quiz_phase2_result_view(request, session_id, index):
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    session_question = get_object_or_404(SessionQuestion, session=session, order_index=index)
    if not session_question.phase2_answered_at:
        return redirect("quiz-phase2", session_id=session.id, index=index)
    question = session_question.question
    ai_options = list(
        question.options.filter(author_type=Option.AuthorType.AI).select_related("llm_model")
    )
    details = []
    assignment_map = session_question.phase2_assignment_json or {}
    for option in ai_options:
        assigned = assignment_map.get(str(option.id))
        correct = option.llm_model.display_group_slug
        details.append(
            {
                "option": option,
                "assigned_group": assigned,
                "correct_group": correct,
                "is_correct": assigned == correct,
            }
        )
    next_url = _next_url_for_session_question(session, index)
    return render(
        request,
        "quiz/phase2_result.html",
        {
            "session": session,
            "session_question": session_question,
            "details": details,
            "next_url": next_url,
        },
    )


@login_required
def quiz_session_result_view(request, session_id):
    session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    total_questions = session.session_questions.count()
    phase1_answered = session.session_questions.exclude(phase1_is_correct__isnull=True).count()
    if session.choice_count == 4:
        phase2_answered = session.session_questions.exclude(phase2_score__isnull=True).count()
    else:
        phase2_answered = total_questions
    if session.status == QuizSession.Status.ACTIVE and phase1_answered == total_questions and phase2_answered == total_questions:
        session.status = QuizSession.Status.FINISHED
        session.finished_at = session.finished_at or timezone.now()
        session.save(update_fields=["status", "finished_at", "updated_at"])

    phase1_correct = session.session_questions.filter(phase1_is_correct=True).count()
    phase1_rate = (phase1_correct / total_questions * 100) if total_questions else 0
    phase2_sum = session.session_questions.aggregate(total=Sum("phase2_score")).get("total") or 0
    phase2_max_points = total_questions * 3 if session.choice_count == 4 else 0
    phase2_rate = (phase2_sum / phase2_max_points * 100) if phase2_max_points else 0
    phase2_perfect = session.session_questions.filter(phase2_is_perfect=True).count()

    total_phase1 = SessionQuestion.objects.filter(session__user=request.user).exclude(
        phase1_is_correct__isnull=True
    )
    total_phase1_count = total_phase1.count()
    total_phase1_correct = total_phase1.filter(phase1_is_correct=True).count()

    total_phase2 = SessionQuestion.objects.filter(
        session__user=request.user,
        session__choice_count=4,
    ).exclude(phase2_score__isnull=True)
    total_phase2_points = total_phase2.aggregate(total=Sum("phase2_score")).get("total") or 0
    total_phase2_count = total_phase2.count()

    return render(
        request,
        "quiz/session_result.html",
        {
            "session": session,
            "phase1_rate": phase1_rate,
            "phase1_correct": phase1_correct,
            "phase1_total": total_questions,
            "phase2_rate": phase2_rate,
            "phase2_sum": phase2_sum,
            "phase2_max_points": phase2_max_points,
            "phase2_perfect": phase2_perfect,
            "total_phase1_count": total_phase1_count,
            "total_phase1_correct": total_phase1_correct,
            "total_phase2_count": total_phase2_count,
            "total_phase2_points": total_phase2_points,
        },
    )

# Create your views here.
