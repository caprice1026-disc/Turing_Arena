import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from uuid import uuid4

from apps.admin_portal.models import AuditLog
from apps.content.models import Genre, LlmModel, Option, Question, Scenario
from apps.content.services.openrouter_client import OpenRouterError, OpenRouterResult
from apps.quiz.models import QuizSession, SessionQuestion, UserSeenQuestion


User = get_user_model()


def _create_admin():
    return User.objects.create_superuser(
        login_id="admin",
        email="admin@example.com",
        password="AdminPass123!",
    )


def _create_user(login_id="user1", email="user1@example.com"):
    return User.objects.create_user(login_id=login_id, email=email, password="UserPass123!")


def _create_models():
    gpt = LlmModel.objects.create(
        provider="openai",
        display_group="GPT系",
        display_group_slug="gpt",
        display_name="GPT",
        api_model_name="openai/gpt",
    )
    claude = LlmModel.objects.create(
        provider="anthropic",
        display_group="Claude系",
        display_group_slug="claude",
        display_name="Claude",
        api_model_name="anthropic/claude",
    )
    gemini = LlmModel.objects.create(
        provider="google",
        display_group="Gemini系",
        display_group_slug="gemini",
        display_name="Gemini",
        api_model_name="google/gemini",
    )
    return gpt, claude, gemini


def _create_question(*, admin_user, difficulty="easy", choice_count=4, model_set=None):
    genre = Genre.objects.create(slug=f"genre-{uuid4().hex[:10]}", name="雑談")
    scenario = Scenario.objects.create(
        user_message_text="こんにちは",
        human_reply_text="やあ",
        genre=genre,
        created_by_admin=admin_user,
    )
    question = Question.objects.create(
        scenario=scenario,
        status=Question.Status.PUBLISHED,
        difficulty=difficulty,
        choice_count=choice_count,
        created_by_admin=admin_user,
    )
    Option.objects.create(
        question=question,
        author_type=Option.AuthorType.HUMAN,
        content_text="やあ",
        generation_status=Option.GenerationStatus.OK,
    )
    if choice_count == 2:
        Option.objects.create(
            question=question,
            author_type=Option.AuthorType.AI,
            llm_model=model_set[0],
            content_text="こんにちは、お手伝いします。",
            generation_status=Option.GenerationStatus.OK,
        )
    else:
        for model in model_set:
            Option.objects.create(
                question=question,
                author_type=Option.AuthorType.AI,
                llm_model=model,
                content_text=f"{model.display_group}の回答",
                generation_status=Option.GenerationStatus.OK,
            )
    return question


@pytest.mark.django_db
def test_signup_login_logout_success(client):
    response = client.post(
        "/signup",
        data={
            "login_id": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        },
    )
    assert response.status_code == 302
    assert response.url == "/"

    response = client.get("/")
    assert response.wsgi_request.user.is_authenticated

    response = client.get("/logout")
    assert response.status_code == 302
    assert response.url == "/"

    response = client.post(
        "/signup",
        data={
            "login_id": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        },
    )
    assert response.status_code == 200
    assert "既に使われています" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_session_start_reserves_question_and_phase1_marks_solved(client):
    admin_user = _create_admin()
    user = _create_user()
    models = _create_models()
    _create_question(admin_user=admin_user, difficulty="easy", choice_count=2, model_set=[models[0]])
    client.force_login(user)

    response = client.post(
        "/quiz/start",
        data={"difficulty": "easy", "choice_count": 2, "num_questions": 1},
    )
    assert response.status_code == 302
    assert "/quiz/session/" in response.url

    session = QuizSession.objects.get(user=user, status=QuizSession.Status.ACTIVE)
    seen = UserSeenQuestion.objects.get(user=user)
    assert seen.status == UserSeenQuestion.Status.RESERVED

    sq = SessionQuestion.objects.get(session=session, order_index=0)
    human_option = sq.question.options.get(author_type=Option.AuthorType.HUMAN)
    human_letter = next(
        letter for letter, option_id in sq.shuffle_map_json.items() if option_id == human_option.id
    )
    response = client.post(
        f"/quiz/session/{session.id}/q/0",
        data={"selected_letter": human_letter, "phase1_time_ms": 100},
    )
    assert response.status_code == 302
    seen.refresh_from_db()
    assert seen.status == UserSeenQuestion.Status.SOLVED
    sq.refresh_from_db()
    assert sq.phase1_is_correct is True


@pytest.mark.django_db
def test_active_session_is_resumed(client):
    admin_user = _create_admin()
    user = _create_user()
    models = _create_models()
    _create_question(admin_user=admin_user, difficulty="easy", choice_count=2, model_set=[models[0]])
    client.force_login(user)

    client.post("/quiz/start", data={"difficulty": "easy", "choice_count": 2, "num_questions": 1})
    first_session = QuizSession.objects.get(user=user, status=QuizSession.Status.ACTIVE)
    response = client.post(
        "/quiz/start",
        data={"difficulty": "easy", "choice_count": 2, "num_questions": 1},
    )
    assert response.status_code == 302
    assert str(first_session.id) in response.url
    assert QuizSession.objects.filter(user=user, status=QuizSession.Status.ACTIVE).count() == 1


@pytest.mark.django_db
def test_out_of_stock_paths(client):
    admin_user = _create_admin()
    user = _create_user()
    models = _create_models()
    _create_question(admin_user=admin_user, difficulty="easy", choice_count=2, model_set=[models[0]])
    client.force_login(user)

    response = client.post("/quiz/start", data={"difficulty": "hard", "choice_count": 2, "num_questions": 1})
    assert response.status_code == 302
    assert "/quiz/out_of_stock" in response.url
    assert "available_count=0" in response.url

    response = client.post("/quiz/start", data={"difficulty": "easy", "choice_count": 2, "num_questions": 3})
    assert response.status_code == 302
    assert "available_count=1" in response.url


@pytest.mark.django_db
def test_phase1_result_hides_human_letter_for_4choice(client):
    admin_user = _create_admin()
    user = _create_user()
    models = _create_models()
    _create_question(admin_user=admin_user, difficulty="easy", choice_count=4, model_set=models)
    client.force_login(user)
    client.post("/quiz/start", data={"difficulty": "easy", "choice_count": 4, "num_questions": 1})
    session = QuizSession.objects.get(user=user, status=QuizSession.Status.ACTIVE)
    sq = SessionQuestion.objects.get(session=session, order_index=0)
    response = client.post(
        f"/quiz/session/{session.id}/q/0",
        data={"selected_letter": "A", "phase1_time_ms": 100},
    )
    assert response.status_code == 302
    response = client.get(f"/quiz/session/{session.id}/q/0/phase1_result")
    body = response.content.decode("utf-8")
    assert "正解の選択肢:" not in body


@pytest.mark.django_db
def test_phase2_duplicate_assignment_rejected_and_scoring(client):
    admin_user = _create_admin()
    user = _create_user()
    models = _create_models()
    _create_question(admin_user=admin_user, difficulty="easy", choice_count=4, model_set=models)
    client.force_login(user)
    client.post("/quiz/start", data={"difficulty": "easy", "choice_count": 4, "num_questions": 1})
    session = QuizSession.objects.get(user=user, status=QuizSession.Status.ACTIVE)
    sq = SessionQuestion.objects.get(session=session, order_index=0)
    human_option = sq.question.options.get(author_type=Option.AuthorType.HUMAN)
    human_letter = next(
        letter for letter, option_id in sq.shuffle_map_json.items() if option_id == human_option.id
    )
    client.post(f"/quiz/session/{session.id}/q/0", data={"selected_letter": human_letter, "phase1_time_ms": 10})

    ai_options = list(sq.question.options.filter(author_type=Option.AuthorType.AI).order_by("id"))
    duplicate_data = {f"option_{option.id}": "gpt" for option in ai_options}
    duplicate_data["phase2_time_ms"] = 33
    response = client.post(f"/quiz/session/{session.id}/q/0/phase2", data=duplicate_data)
    assert response.status_code == 200
    assert "同じモデル系統は1回のみ選択できます" in response.content.decode("utf-8")

    correct_data = {
        f"option_{option.id}": option.llm_model.display_group_slug for option in ai_options
    }
    correct_data["phase2_time_ms"] = 45
    response = client.post(f"/quiz/session/{session.id}/q/0/phase2", data=correct_data)
    assert response.status_code == 302
    sq.refresh_from_db()
    assert sq.phase2_score == 3
    assert sq.phase2_is_perfect is True


@pytest.mark.django_db
def test_ranking_respects_min_attempts(client):
    admin_user = _create_admin()
    strong_user = _create_user("strong", "strong@example.com")
    weak_user = _create_user("weak", "weak@example.com")
    _create_models()

    for idx in range(10):
        session = QuizSession.objects.create(
            user=strong_user,
            difficulty="easy",
            choice_count=4,
            num_questions_requested=1,
            status=QuizSession.Status.FINISHED,
        )
        SessionQuestion.objects.create(
            session=session,
            question=_create_question(
                admin_user=admin_user,
                difficulty="easy",
                choice_count=4,
                model_set=LlmModel.objects.all()[:3],
            ),
            order_index=0,
            shuffle_map_json={"A": 1, "B": 2, "C": 3, "D": 4},
            phase1_selected_letter="A",
            phase1_is_correct=True,
            phase1_answered_at=timezone.now(),
            phase2_assignment_json={"1": "gpt", "2": "claude", "3": "gemini"},
            phase2_score=3,
            phase2_is_perfect=True,
            phase2_answered_at=timezone.now(),
        )

    weak_session = QuizSession.objects.create(
        user=weak_user,
        difficulty="easy",
        choice_count=4,
        num_questions_requested=1,
        status=QuizSession.Status.FINISHED,
    )
    SessionQuestion.objects.create(
        session=weak_session,
        question=Question.objects.first(),
        order_index=0,
        shuffle_map_json={"A": 1, "B": 2, "C": 3, "D": 4},
        phase1_selected_letter="A",
        phase1_is_correct=True,
        phase1_answered_at=timezone.now(),
        phase2_assignment_json={"1": "gpt", "2": "claude", "3": "gemini"},
        phase2_score=3,
        phase2_is_perfect=True,
        phase2_answered_at=timezone.now(),
    )

    response = client.get("/ranking")
    body = response.content.decode("utf-8")
    assert "strong" in body
    assert "weak" not in body


@pytest.mark.django_db
def test_admin_question_wizard_success_and_failure_retry(client, monkeypatch):
    admin_user = _create_admin()
    client.force_login(admin_user)
    genre = Genre.objects.create(slug="zatsudan", name="雑談")
    gpt, claude, gemini = _create_models()

    def fake_generate(**kwargs):
        return OpenRouterResult(
            content_text=f"generated-{kwargs['api_model_name']}",
            response_payload={"id": "x", "model": kwargs["api_model_name"], "created": 1, "usage": {}},
            request_payload={"model": kwargs["api_model_name"]},
        )

    monkeypatch.setattr("apps.admin_portal.services.question_wizard_service.generate", fake_generate)
    response = client.post(
        "/admin/questions/create",
        data={
            "user_message_text": "質問",
            "human_reply_text": "人間回答",
            "genre_id": genre.id,
            "tag_ids": "",
            "choice_count": 4,
            "selected_model_ids": [str(gpt.id), str(claude.id), str(gemini.id)],
            "system_prompt": "prompt",
            "difficulty": "easy",
            "publish_now": "on",
        },
    )
    assert response.status_code == 302
    question = Question.objects.latest("id")
    assert question.status == Question.Status.PUBLISHED
    assert question.options.count() == 4
    assert question.options.filter(generation_status=Option.GenerationStatus.OK).count() == 4
    assert AuditLog.objects.filter(
        event_type=AuditLog.EventType.QUESTION_PUBLISH, target_question=question
    ).exists()

    def fake_error(**kwargs):
        raise OpenRouterError("boom", status_code=500, retryable=True)

    monkeypatch.setattr("apps.admin_portal.services.question_wizard_service.generate", fake_error)
    response = client.post(
        "/admin/questions/create",
        data={
            "user_message_text": "質問2",
            "human_reply_text": "人間回答2",
            "genre_id": genre.id,
            "tag_ids": "",
            "choice_count": 2,
            "selected_model_ids": [str(gpt.id)],
            "difficulty": "easy",
            "publish_now": "",
        },
    )
    assert response.status_code == 302
    failed_question = Question.objects.latest("id")
    failed_option = failed_question.options.get(author_type=Option.AuthorType.AI)
    assert failed_option.generation_status == Option.GenerationStatus.ERROR

    monkeypatch.setattr("apps.admin_portal.services.question_wizard_service.generate", fake_generate)
    response = client.get(f"/admin/options/{failed_option.id}/retry")
    assert response.status_code == 302
    failed_option.refresh_from_db()
    assert failed_option.generation_status == Option.GenerationStatus.OK


@pytest.mark.django_db
def test_force_password_reset_creates_audit_log(client):
    admin_user = _create_admin()
    target = _create_user("reset-target", "target@example.com")
    client.force_login(admin_user)
    response = client.post(
        f"/admin/users/{target.id}/force_password_reset",
        data={"new_password": "ChangedPass123!"},
    )
    assert response.status_code == 302
    target.refresh_from_db()
    assert target.check_password("ChangedPass123!")
    assert AuditLog.objects.filter(
        event_type=AuditLog.EventType.USER_PASSWORD_RESET,
        actor=admin_user,
        target_user=target,
    ).exists()


@pytest.mark.django_db
def test_admin_question_list_page_renders(client):
    admin_user = _create_admin()
    models = _create_models()
    _create_question(admin_user=admin_user, difficulty="easy", choice_count=4, model_set=models)
    client.force_login(admin_user)
    response = client.get("/admin/questions")
    assert response.status_code == 200
    assert "問題一覧" in response.content.decode("utf-8")
