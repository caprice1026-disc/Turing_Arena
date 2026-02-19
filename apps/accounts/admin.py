from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("login_id", "email", "is_staff", "is_active")
    ordering = ("login_id",)
    search_fields = ("login_id", "email")
    fieldsets = (
        (None, {"fields": ("login_id", "email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("login_id", "email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )

# Register your models here.
