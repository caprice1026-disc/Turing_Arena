from django.urls import path

from . import views


urlpatterns = [
    path("quiz/start", views.quiz_start_view, name="quiz-start"),
    path("quiz/out_of_stock", views.quiz_out_of_stock_view, name="quiz-out-of-stock"),
    path(
        "quiz/session/<int:session_id>/q/<int:index>",
        views.quiz_question_view,
        name="quiz-question",
    ),
    path(
        "quiz/session/<int:session_id>/q/<int:index>/phase1_result",
        views.quiz_phase1_result_view,
        name="quiz-phase1-result",
    ),
    path(
        "quiz/session/<int:session_id>/q/<int:index>/phase2",
        views.quiz_phase2_view,
        name="quiz-phase2",
    ),
    path(
        "quiz/session/<int:session_id>/q/<int:index>/phase2_result",
        views.quiz_phase2_result_view,
        name="quiz-phase2-result",
    ),
    path(
        "quiz/session/<int:session_id>/result",
        views.quiz_session_result_view,
        name="quiz-session-result",
    ),
]
