from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class LoginIdOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        login_value = kwargs.get("login_value") or username
        if not login_value or not password:
            return None
        user_model = get_user_model()
        try:
            user = user_model.objects.get(
                Q(login_id__iexact=login_value) | Q(email__iexact=login_value)
            )
        except user_model.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
