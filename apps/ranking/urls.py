from django.urls import path

from .views import ranking_view


urlpatterns = [
    path("ranking", ranking_view, name="ranking"),
]
