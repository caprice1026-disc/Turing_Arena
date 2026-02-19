from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Genre(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, default="style")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Scenario(models.Model):
    user_message_text = models.TextField()
    human_reply_text = models.TextField()
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="scenarios")
    created_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_scenarios",
    )
    tags = models.ManyToManyField(Tag, through="ScenarioTag", related_name="scenarios")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Scenario#{self.pk}"


class ScenarioTag(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "tag"], name="unique_scenario_tag_pair"
            )
        ]


class LlmModel(models.Model):
    provider = models.CharField(max_length=50)
    display_group = models.CharField(max_length=50)
    display_group_slug = models.SlugField(max_length=50)
    display_name = models.CharField(max_length=100)
    api_model_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    deprecated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "api_model_name"], name="unique_provider_api_model"
            ),
            models.UniqueConstraint(
                fields=["display_group_slug"], name="unique_display_group_slug"
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.api_model_name})"


class GenerationProfile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    params_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        NORMAL = "normal", "Normal"
        HARD = "hard", "Hard"

    scenario = models.ForeignKey(Scenario, on_delete=models.PROTECT, related_name="questions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    difficulty = models.CharField(
        max_length=20, choices=Difficulty.choices, default=Difficulty.NORMAL
    )
    choice_count = models.PositiveSmallIntegerField(default=4)
    generation_profile = models.ForeignKey(
        GenerationProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="questions",
    )
    variant_of_question = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="variants",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.choice_count not in (2, 4):
            raise ValidationError("choice_count must be 2 or 4.")

    def __str__(self):
        return f"Question#{self.pk}"


class Option(models.Model):
    class AuthorType(models.TextChoices):
        HUMAN = "human", "Human"
        AI = "ai", "AI"

    class GenerationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        OK = "ok", "Ok"
        ERROR = "error", "Error"

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    author_type = models.CharField(max_length=20, choices=AuthorType.choices)
    llm_model = models.ForeignKey(
        LlmModel,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="options",
    )
    content_text = models.TextField(blank=True)
    system_prompt = models.TextField(blank=True, null=True)
    temperature = models.FloatField(blank=True, null=True)
    seed = models.IntegerField(blank=True, null=True)
    max_tokens = models.IntegerField(blank=True, null=True)
    request_payload_json = models.JSONField(blank=True, null=True)
    response_payload_json = models.JSONField(blank=True, null=True)
    generation_status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
    )
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.author_type == self.AuthorType.HUMAN and self.llm_model_id:
            raise ValidationError("Human option cannot have llm_model.")
        if self.author_type == self.AuthorType.AI and not self.llm_model_id:
            raise ValidationError("AI option must have llm_model.")

    def __str__(self):
        return f"Option#{self.pk} ({self.author_type})"

# Create your models here.
