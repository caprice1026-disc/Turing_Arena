from django.contrib import admin

from .models import (
    GenerationProfile,
    Genre,
    LlmModel,
    Option,
    Question,
    Scenario,
    ScenarioTag,
    Tag,
)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "name", "is_active")
    search_fields = ("slug", "name")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_active")
    search_fields = ("name", "category")


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("id", "genre", "created_by_admin", "created_at")
    search_fields = ("id", "user_message_text", "human_reply_text")
    list_filter = ("genre",)


@admin.register(ScenarioTag)
class ScenarioTagAdmin(admin.ModelAdmin):
    list_display = ("scenario", "tag")


@admin.register(LlmModel)
class LlmModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "display_group",
        "display_group_slug",
        "display_name",
        "api_model_name",
        "is_active",
    )
    search_fields = ("provider", "display_group", "display_name", "api_model_name")


@admin.register(GenerationProfile)
class GenerationProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "scenario", "difficulty", "choice_count", "status", "published_at")
    list_filter = ("status", "difficulty", "choice_count")
    search_fields = ("id", "scenario__user_message_text")
    inlines = [OptionInline]


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "author_type", "llm_model", "generation_status", "created_at")
    list_filter = ("author_type", "generation_status")

# Register your models here.
