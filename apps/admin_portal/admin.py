from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "actor", "target_user", "target_question", "created_at")
    list_filter = ("event_type",)
    search_fields = ("actor__login_id", "target_user__login_id", "target_question__id")

# Register your models here.
