from django.contrib import admin

from .models import QuizSession, SessionQuestion, UserSeenQuestion


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "difficulty",
        "choice_count",
        "num_questions_requested",
        "status",
        "started_at",
    )
    list_filter = ("status", "difficulty", "choice_count")
    search_fields = ("id", "user__login_id", "user__email")


@admin.register(SessionQuestion)
class SessionQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "question", "order_index", "phase1_is_correct", "phase2_score")
    list_filter = ("phase1_is_correct", "phase2_is_perfect")
    search_fields = ("id", "session__id", "question__id")


@admin.register(UserSeenQuestion)
class UserSeenQuestionAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "status", "session", "reserved_until", "solved_at")
    list_filter = ("status",)

# Register your models here.
