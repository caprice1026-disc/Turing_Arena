from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, SignUpForm


@require_http_methods(["GET", "POST"])
def signup_view(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="apps.accounts.auth_backends.LoginIdOrEmailBackend")
        messages.success(request, "登録が完了しました。")
        return redirect("home")
    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user, backend="apps.accounts.auth_backends.LoginIdOrEmailBackend")
        messages.success(request, "ログインしました。")
        return redirect("home")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "ログアウトしました。")
    return redirect("home")

# Create your views here.
