from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class EventType(models.TextChoices):
        QUESTION_PUBLISH = "question_publish", "Question Publish"
        QUESTION_ARCHIVE = "question_archive", "Question Archive"
        USER_PASSWORD_RESET = "user_password_reset", "User Password Reset"

    event_type = models.CharField(max_length=50, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="targeted_audit_events",
    )
    target_question = models.ForeignKey(
        "content.Question",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} by {self.actor_id}"

# Create your models here.
