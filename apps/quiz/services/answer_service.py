from django.db import transaction
from django.utils import timezone

from apps.content.models import Option
from apps.quiz.models import UserSeenQuestion


def _get_human_option_id(question):
    return question.options.get(author_type=Option.AuthorType.HUMAN).id


@transaction.atomic
def submit_phase1(*, session_question, selected_letter, phase1_time_ms=None):
    selected_letter = (selected_letter or "").upper().strip()
    option_id = session_question.shuffle_map_json.get(selected_letter)
    if not option_id:
        raise ValueError("Invalid selected letter.")

    human_option_id = _get_human_option_id(session_question.question)
    is_correct = option_id == human_option_id
    now = timezone.now()

    session_question.phase1_selected_letter = selected_letter
    session_question.phase1_is_correct = is_correct
    session_question.phase1_answered_at = now
    session_question.phase1_time_ms = phase1_time_ms
    session_question.save(
        update_fields=[
            "phase1_selected_letter",
            "phase1_is_correct",
            "phase1_answered_at",
            "phase1_time_ms",
            "updated_at",
        ]
    )

    seen = UserSeenQuestion.objects.filter(
        user=session_question.session.user,
        question=session_question.question,
    ).first()
    if seen:
        seen.status = UserSeenQuestion.Status.SOLVED
        seen.solved_at = now
        seen.reserved_until = None
        seen.save(update_fields=["status", "solved_at", "reserved_until"])

    return {
        "is_correct": is_correct,
        "human_option_id": human_option_id,
        "selected_option_id": option_id,
    }


@transaction.atomic
def submit_phase2(*, session_question, assignment_map, phase2_time_ms=None):
    question = session_question.question
    if question.choice_count != 4:
        raise ValueError("Phase2 is only available for 4-choice questions.")

    human_option_id = _get_human_option_id(question)
    ai_options = list(
        question.options.filter(author_type=Option.AuthorType.AI).select_related("llm_model")
    )
    expected_option_ids = {str(option.id) for option in ai_options}
    actual_option_ids = set(assignment_map.keys())
    if expected_option_ids != actual_option_ids:
        raise ValueError("Invalid option set for phase2 assignment.")

    assigned_groups = list(assignment_map.values())
    if len(set(assigned_groups)) != 3:
        raise ValueError("Duplicate display groups are not allowed.")

    expected_groups = {option.llm_model.display_group_slug for option in ai_options}
    if set(assigned_groups) != expected_groups:
        raise ValueError("Assigned groups must match the question model groups.")

    score = 0
    details = []
    for option in ai_options:
        assigned_group = assignment_map[str(option.id)]
        correct_group = option.llm_model.display_group_slug
        matched = assigned_group == correct_group
        if matched:
            score += 1
        details.append(
            {
                "option_id": option.id,
                "assigned_group": assigned_group,
                "correct_group": correct_group,
                "is_correct": matched,
            }
        )

    is_perfect = score == 3
    now = timezone.now()
    session_question.phase2_assignment_json = assignment_map
    session_question.phase2_score = score
    session_question.phase2_is_perfect = is_perfect
    session_question.phase2_answered_at = now
    session_question.phase2_time_ms = phase2_time_ms
    session_question.save(
        update_fields=[
            "phase2_assignment_json",
            "phase2_score",
            "phase2_is_perfect",
            "phase2_answered_at",
            "phase2_time_ms",
            "updated_at",
        ]
    )
    return {
        "score": score,
        "is_perfect": is_perfect,
        "details": details,
        "human_option_id": human_option_id,
    }
