from django.urls import path

from . import views


urlpatterns = [
    path("admin/dashboard", views.admin_dashboard_view, name="admin-dashboard"),
    path("admin/questions/create", views.question_create_view, name="admin-question-create"),
    path("admin/questions", views.question_list_view, name="admin-question-list"),
    path("admin/options/<int:option_id>/retry", views.option_retry_view, name="admin-option-retry"),
    path("admin/users", views.user_list_view, name="admin-user-list"),
    path(
        "admin/users/<int:user_id>/force_password_reset",
        views.force_password_reset_view,
        name="admin-force-password-reset",
    ),
]
