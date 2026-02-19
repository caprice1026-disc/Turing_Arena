from django import forms

from apps.content.models import LlmModel, Question


class QuestionWizardForm(forms.Form):
    user_message_text = forms.CharField(widget=forms.Textarea, required=True)
    human_reply_text = forms.CharField(widget=forms.Textarea, required=True)
    genre_id = forms.IntegerField(min_value=1, required=True)
    tag_ids = forms.CharField(required=False, help_text="カンマ区切りでTag IDを指定")
    choice_count = forms.TypedChoiceField(choices=[(2, "2択"), (4, "4択")], coerce=int)
    selected_model_ids = forms.MultipleChoiceField(required=True, choices=[])
    system_prompt = forms.CharField(widget=forms.Textarea, required=False)
    temperature = forms.FloatField(required=False)
    seed = forms.IntegerField(required=False)
    max_tokens = forms.IntegerField(required=False, min_value=1)
    generation_profile_id = forms.IntegerField(required=False, min_value=1)
    difficulty = forms.ChoiceField(choices=Question.Difficulty.choices)
    publish_now = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_choices = [
            (str(model.id), f"{model.display_name} ({model.api_model_name})")
            for model in LlmModel.objects.filter(is_active=True).order_by("provider", "display_name")
        ]
        self.fields["selected_model_ids"].choices = model_choices

    def clean_selected_model_ids(self):
        model_ids = [int(value) for value in self.cleaned_data["selected_model_ids"]]
        if len(model_ids) != len(set(model_ids)):
            raise forms.ValidationError("同じモデルを重複して選択できません。")
        return model_ids

    def clean(self):
        cleaned = super().clean()
        choice_count = cleaned.get("choice_count")
        model_ids = cleaned.get("selected_model_ids") or []
        if choice_count == 4 and len(model_ids) != 3:
            raise forms.ValidationError("4択では3つのAIモデルが必要です。")
        if choice_count == 2 and len(model_ids) != 1:
            raise forms.ValidationError("2択では1つのAIモデルが必要です。")
        return cleaned


class ForcePasswordResetForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, min_length=8)
