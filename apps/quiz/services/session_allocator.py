import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.content.models import Option, Question
from apps.quiz.models import QuizSession, SessionQuestion, UserSeenQuestion


def _cleanup_expired_reservations(user):
    now = timezone.now()
    UserSeenQuestion.objects.filter(
        user=user,
        status=UserSeenQuestion.Status.RESERVED,
        reserved_until__lt=now,
    ).delete()


def _letter_sequence(choice_count):
    return ["A", "B"] if choice_count == 2 else ["A", "B", "C", "D"]


def _eligible_questions_queryset(difficulty, choice_count):
    queryset = (
        Question.objects.filter(
            status=Question.Status.PUBLISHED,
            difficulty=difficulty,
            choice_count=choice_count,
        )
        .annotate(
            option_count=Count("options"),
            human_count=Count(
                "options", filter=Q(options__author_type=Option.AuthorType.HUMAN)
            ),
            ai_count=Count("options", filter=Q(options__author_type=Option.AuthorType.AI)),
            ok_count=Count(
                "options",
                filter=Q(options__generation_status=Option.GenerationStatus.OK),
            ),
            ai_model_count=Count(
                "options__llm_model",
                filter=Q(options__author_type=Option.AuthorType.AI),
                distinct=True,
            ),
        )
        .filter(
            option_count=choice_count,
            human_count=1,
            ai_count=choice_count - 1,
            ok_count=choice_count,
        )
    )
    if choice_count == 4:
        queryset = queryset.filter(ai_model_count=3)
    return queryset


def _build_shuffle_map(question, choice_count):
    option_ids = list(question.options.values_list("id", flat=True))
    random.shuffle(option_ids)
    letters = _letter_sequence(choice_count)
    return {letter: option_id for letter, option_id in zip(letters, option_ids)}


def start_or_resume_session(
    *,
    user,
    difficulty,
    choice_count,
    num_questions_requested,
    restart=False,
    force_num_questions=None,
):
    if num_questions_requested not in settings.ALLOWED_NUM_QUESTIONS:
        raise ValueError("Requested num_questions is not allowed by feature flag.")
    if choice_count not in (2, 4):
        raise ValueError("choice_count must be 2 or 4.")

    _cleanup_expired_reservations(user)
    active_session = (
        QuizSession.objects.filter(user=user, status=QuizSession.Status.ACTIVE)
        .order_by("-id")
        .first()
    )
    if active_session and not restart:
        return {
            "session": active_session,
            "resumed": True,
            "out_of_stock": False,
            "available_count": None,
        }
    if active_session and restart:
        abandon_session(session=active_session, user=user)

    seen_question_ids = UserSeenQuestion.objects.filter(user=user).filter(
        Q(status=UserSeenQuestion.Status.SOLVED)
        | Q(
            status=UserSeenQuestion.Status.RESERVED,
            reserved_until__gt=timezone.now(),
        )
    )
    seen_question_ids = seen_question_ids.values_list("question_id", flat=True)

    candidates = _eligible_questions_queryset(difficulty, choice_count).exclude(
        id__in=seen_question_ids
    )
    available_count = candidates.count()
    if available_count <= 0:
        return {
            "session": None,
            "resumed": False,
            "out_of_stock": True,
            "available_count": 0,
        }

    requested = force_num_questions or num_questions_requested
    if requested > available_count:
        return {
            "session": None,
            "resumed": False,
            "out_of_stock": True,
            "available_count": available_count,
        }

    selected_question_ids = list(
        candidates.order_by("?").values_list("id", flat=True)[:requested]
    )
    reserve_ttl = timezone.now() + timedelta(hours=settings.RESERVE_TTL_HOURS)

    with transaction.atomic():
        session = QuizSession.objects.create(
            user=user,
            difficulty=difficulty,
            choice_count=choice_count,
            num_questions_requested=requested,
            status=QuizSession.Status.ACTIVE,
        )
        questions = Question.objects.filter(id__in=selected_question_ids).prefetch_related(
            "options"
        )
        question_by_id = {question.id: question for question in questions}
        for order_index, question_id in enumerate(selected_question_ids):
            question = question_by_id[question_id]
            UserSeenQuestion.objects.update_or_create(
                user=user,
                question=question,
                defaults={
                    "status": UserSeenQuestion.Status.RESERVED,
                    "session": session,
                    "reserved_until": reserve_ttl,
                },
            )
            SessionQuestion.objects.create(
                session=session,
                question=question,
                order_index=order_index,
                shuffle_map_json=_build_shuffle_map(question, choice_count),
            )
    return {
        "session": session,
        "resumed": False,
        "out_of_stock": False,
        "available_count": available_count,
    }


def abandon_session(*, session, user):
    with transaction.atomic():
        session.status = QuizSession.Status.ABANDONED
        session.save(update_fields=["status", "updated_at"])
        UserSeenQuestion.objects.filter(
            user=user,
            session=session,
            status=UserSeenQuestion.Status.RESERVED,
        ).delete()
