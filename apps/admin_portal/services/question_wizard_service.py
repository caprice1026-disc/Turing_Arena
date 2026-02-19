from apps.content.models import LlmModel, Option
from apps.content.services.openrouter_client import OpenRouterError, generate


def _build_system_prompt(base_prompt):
    return (base_prompt or "").strip()


def ensure_human_option(question):
    human_option, _ = Option.objects.get_or_create(
        question=question,
        author_type=Option.AuthorType.HUMAN,
        defaults={
            "content_text": question.scenario.human_reply_text,
            "generation_status": Option.GenerationStatus.OK,
        },
    )
    if human_option.content_text != question.scenario.human_reply_text:
        human_option.content_text = question.scenario.human_reply_text
        human_option.generation_status = Option.GenerationStatus.OK
        human_option.error_message = ""
        human_option.save(
            update_fields=["content_text", "generation_status", "error_message", "updated_at"]
        )
    return human_option


def _run_generation_for_model(
    *,
    question,
    llm_model,
    system_prompt,
    temperature=None,
    seed=None,
    max_tokens=None,
):
    option, _ = Option.objects.get_or_create(
        question=question,
        author_type=Option.AuthorType.AI,
        llm_model=llm_model,
        defaults={
            "generation_status": Option.GenerationStatus.PENDING,
        },
    )
    option.system_prompt = system_prompt
    option.temperature = temperature
    option.seed = seed
    option.max_tokens = max_tokens
    option.generation_status = Option.GenerationStatus.PENDING
    option.error_message = ""
    option.save(
        update_fields=[
            "system_prompt",
            "temperature",
            "seed",
            "max_tokens",
            "generation_status",
            "error_message",
            "updated_at",
        ]
    )
    try:
        result = generate(
            api_model_name=llm_model.api_model_name,
            user_prompt=question.scenario.user_message_text,
            system_prompt=system_prompt,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
        )
    except OpenRouterError as exc:
        option.generation_status = Option.GenerationStatus.ERROR
        option.error_message = (
            f"{exc.status_code or 'network'}:{str(exc)[:220]}:{(exc.response_text or '')[:220]}"
        )
        option.save(update_fields=["generation_status", "error_message", "updated_at"])
        return option

    option.content_text = result.content_text
    option.request_payload_json = result.request_payload
    option.response_payload_json = result.response_payload
    option.generation_status = Option.GenerationStatus.OK
    option.error_message = ""
    option.save(
        update_fields=[
            "content_text",
            "request_payload_json",
            "response_payload_json",
            "generation_status",
            "error_message",
            "updated_at",
        ]
    )
    return option


def generate_and_persist_options(
    *,
    question,
    selected_model_ids,
    system_prompt="",
    temperature=None,
    seed=None,
    max_tokens=None,
):
    ensure_human_option(question)
    models = list(LlmModel.objects.filter(id__in=selected_model_ids, is_active=True))
    model_by_id = {model.id: model for model in models}
    generated_options = []
    final_system_prompt = _build_system_prompt(system_prompt)
    for model_id in selected_model_ids:
        llm_model = model_by_id.get(int(model_id))
        if not llm_model:
            continue
        generated = _run_generation_for_model(
            question=question,
            llm_model=llm_model,
            system_prompt=final_system_prompt,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
        )
        generated_options.append(generated)
    return generated_options


def retry_option_generation(option):
    if option.author_type != Option.AuthorType.AI:
        return option
    return _run_generation_for_model(
        question=option.question,
        llm_model=option.llm_model,
        system_prompt=option.system_prompt or "",
        temperature=option.temperature,
        seed=option.seed,
        max_tokens=option.max_tokens,
    )
