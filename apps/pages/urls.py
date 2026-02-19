from django.urls import path

from . import views


urlpatterns = [
    path("", views.home_view, name="home"),
    path("transparency", views.transparency_view, name="transparency"),
]
