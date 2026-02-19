from django.conf import settings
from django.db import models


class QuizSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FINISHED = "finished", "Finished"
        ABANDONED = "abandoned", "Abandoned"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_sessions",
    )
    difficulty = models.CharField(max_length=20)
    choice_count = models.PositiveSmallIntegerField()
    num_questions_requested = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"QuizSession#{self.pk}"


class SessionQuestion(models.Model):
    session = models.ForeignKey(
        QuizSession,
        on_delete=models.CASCADE,
        related_name="session_questions",
    )
    question = models.ForeignKey(
        "content.Question",
        on_delete=models.PROTECT,
        related_name="session_questions",
    )
    order_index = models.PositiveIntegerField()
    shuffle_map_json = models.JSONField(default=dict)
    phase1_selected_letter = models.CharField(max_length=1, blank=True, null=True)
    phase1_is_correct = models.BooleanField(null=True, blank=True)
    phase1_answered_at = models.DateTimeField(blank=True, null=True)
    phase1_time_ms = models.IntegerField(blank=True, null=True)
    phase2_assignment_json = models.JSONField(blank=True, null=True)
    phase2_score = models.IntegerField(blank=True, null=True)
    phase2_is_perfect = models.BooleanField(blank=True, null=True)
    phase2_answered_at = models.DateTimeField(blank=True, null=True)
    phase2_time_ms = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "order_index"], name="unique_order_per_session"
            ),
            models.UniqueConstraint(
                fields=["session", "question"], name="unique_question_per_session"
            ),
        ]
        ordering = ["order_index"]

    def __str__(self):
        return f"SessionQuestion#{self.pk}"


class UserSeenQuestion(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        SOLVED = "solved", "Solved"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seen_questions",
    )
    question = models.ForeignKey(
        "content.Question",
        on_delete=models.CASCADE,
        related_name="seen_by_users",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    session = models.ForeignKey(
        QuizSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seen_questions",
    )
    reserved_until = models.DateTimeField(null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    solved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"], name="unique_seen_question_per_user"
            )
        ]

    def __str__(self):
        return f"UserSeenQuestion(user={self.user_id}, question={self.question_id})"

# Create your models here.
