from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()


class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password_confirm = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = ["login_id", "email", "password", "password_confirm"]

    def clean_login_id(self):
        login_id = self.cleaned_data["login_id"].strip()
        if User.objects.filter(login_id__iexact=login_id).exists():
            raise ValidationError("このlogin_idは既に使われています。")
        return login_id

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("このemailは既に使われています。")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        password_confirm = cleaned.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise ValidationError("パスワードが一致しません。")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    login_value = forms.CharField(label="login_id または email")
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        login_value = cleaned.get("login_value", "").strip()
        password = cleaned.get("password")
        user = authenticate(login_value=login_value, password=password)
        if not user:
            raise ValidationError("認証に失敗しました。")
        cleaned["user"] = user
        return cleaned
