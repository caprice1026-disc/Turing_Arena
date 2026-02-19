from django import forms
from django.conf import settings

from apps.content.models import Question


class QuizStartForm(forms.Form):
    difficulty = forms.ChoiceField(choices=Question.Difficulty.choices)
    choice_count = forms.TypedChoiceField(choices=[(2, "2択"), (4, "4択")], coerce=int)
    num_questions = forms.TypedChoiceField(
        choices=[(value, str(value)) for value in settings.ALLOWED_NUM_QUESTIONS],
        coerce=int,
    )


class Phase1Form(forms.Form):
    selected_letter = forms.ChoiceField(choices=[], required=True)
    phase1_time_ms = forms.IntegerField(required=False, min_value=0)

    def __init__(self, *args, available_letters=None, **kwargs):
        super().__init__(*args, **kwargs)
        letters = available_letters or []
        self.fields["selected_letter"].choices = [(letter, letter) for letter in letters]


class Phase2Form(forms.Form):
    phase2_time_ms = forms.IntegerField(required=False, min_value=0)

    def __init__(self, *args, ai_options=None, group_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        ai_options = ai_options or []
        group_choices = group_choices or []
        for option in ai_options:
            field_name = f"option_{option.id}"
            self.fields[field_name] = forms.ChoiceField(
                choices=[(value, label) for value, label in group_choices],
                required=True,
            )
