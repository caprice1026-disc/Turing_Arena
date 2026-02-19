import random
import time
from dataclasses import dataclass

import httpx
from django.conf import settings


class OpenRouterError(Exception):
    def __init__(self, message, status_code=None, retryable=False, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.response_text = response_text


@dataclass
class OpenRouterResult:
    content_text: str
    response_payload: dict
    request_payload: dict


def _sleep_backoff(attempt_index):
    backoff_seconds = min(2**attempt_index, 8)
    jitter = random.uniform(0, 0.25)
    time.sleep(backoff_seconds + jitter)


def generate(
    *,
    api_model_name,
    user_prompt,
    system_prompt="",
    temperature=None,
    seed=None,
    max_tokens=None,
):
    if not settings.OPENROUTER_API_KEY:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured.")

    payload = {
        "model": api_model_name,
        "messages": [
            {"role": "system", "content": system_prompt or ""},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if seed is not None:
        payload["seed"] = seed
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    max_attempts = max(settings.OPENROUTER_MAX_RETRIES, 1)
    last_error = None
    timeout = settings.OPENROUTER_TIMEOUT_SECONDS
    endpoint = f"{settings.OPENROUTER_BASE_URL}/chat/completions"

    with httpx.Client(timeout=timeout) as client:
        for attempt in range(max_attempts):
            try:
                response = client.post(endpoint, json=payload, headers=headers)
            except httpx.RequestError as exc:
                last_error = OpenRouterError(
                    f"Network error: {exc}",
                    retryable=True,
                )
                if attempt < max_attempts - 1:
                    _sleep_backoff(attempt)
                    continue
                raise last_error from exc

            if response.status_code in (429, 500, 502, 503, 504):
                last_error = OpenRouterError(
                    "Retryable OpenRouter error",
                    status_code=response.status_code,
                    retryable=True,
                    response_text=response.text[:500],
                )
                if attempt < max_attempts - 1:
                    _sleep_backoff(attempt)
                    continue
                raise last_error

            if response.status_code in (400, 401, 402):
                raise OpenRouterError(
                    "Non-retryable OpenRouter error",
                    status_code=response.status_code,
                    retryable=False,
                    response_text=response.text[:500],
                )

            if response.status_code >= 400:
                raise OpenRouterError(
                    "Unexpected OpenRouter error",
                    status_code=response.status_code,
                    retryable=False,
                    response_text=response.text[:500],
                )

            data = response.json()
            try:
                content_text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise OpenRouterError("Invalid OpenRouter response format") from exc

            response_payload = {
                "id": data.get("id"),
                "model": data.get("model"),
                "created": data.get("created"),
                "usage": data.get("usage", {}),
            }
            request_payload = {
                "model": api_model_name,
                "temperature": temperature,
                "seed": seed,
                "max_tokens": max_tokens,
            }
            return OpenRouterResult(
                content_text=content_text,
                response_payload=response_payload,
                request_payload=request_payload,
            )

    if last_error:
        raise last_error
    raise OpenRouterError("Unknown OpenRouter error")
