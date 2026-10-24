"""The single place that calls an LLM (Gemini, or any OpenAI-compatible API such as Groq).

Every call asks for JSON matching a Pydantic schema, uses a low thinking
level to keep cost down, and records token usage so evaluation runs can
report what they actually cost. Tests replace `_generate`.
"""

import copy
import logging
import re
import time
from dataclasses import dataclass, field

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import settings
from app.services.ai_status import OPENAI_COMPATIBLE

logger = logging.getLogger(__name__)

# USD per token for gemini-3-flash-preview (paid tier, checked 2026-10-24).
GEMINI_INPUT_PRICE = 0.50 / 1_000_000
GEMINI_OUTPUT_PRICE = 3.00 / 1_000_000  # includes thinking tokens
REQUEST_TIMEOUT_SECONDS = 120.0


def prices() -> tuple[float, float]:
    """USD per input and output token for the configured provider."""
    if settings.LLM_PROVIDER == OPENAI_COMPATIBLE:
        return settings.LLM_INPUT_PRICE_PER_M / 1_000_000, settings.LLM_OUTPUT_PRICE_PER_M / 1_000_000
    return GEMINI_INPUT_PRICE, GEMINI_OUTPUT_PRICE


# Typographic hyphens and no-break spaces some models emit (gpt-oss writes "end\u2011to\u2011end").
# They look normal but break keyword matching here and in applicant tracking systems.
_PLAIN = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u00a0": " ", "\u2007": " ",
                        "\u2009": " ", "\u202f": " "})


def _plain(value):
    if isinstance(value, str):
        return value.translate(_PLAIN)
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


class RateLimited(Exception):
    """The provider refused the call for now; it may be retried after retry_after seconds."""

    def __init__(self, retry_after: float):
        super().__init__(f"rate limited; retry in {retry_after:.0f}s")
        self.retry_after = retry_after


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        input_price, output_price = prices()
        return self.input_tokens * input_price + self.output_tokens * output_price

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens


@dataclass
class UsageLog:
    """Running totals for the process; the evaluation harness reads and resets it."""
    by_purpose: dict[str, Usage] = field(default_factory=dict)

    def record(self, purpose: str, input_tokens: int, output_tokens: int) -> None:
        self.by_purpose.setdefault(purpose, Usage()).add(input_tokens, output_tokens)

    @property
    def total(self) -> Usage:
        total = Usage()
        for usage in self.by_purpose.values():
            total.calls += usage.calls
            total.input_tokens += usage.input_tokens
            total.output_tokens += usage.output_tokens
        return total


usage_log = UsageLog()
_client: genai.Client | None = None
_last_call = 0.0
# Minimum seconds between calls; the evaluation harness sets this to stay under free-tier limits.
min_interval_seconds = 0.0
# Every call may wait at least this long on rate limits; the evaluation harness raises it so short
# per-minute limits are waited out instead of measuring the basic-mode fallback.
min_wait_seconds = 0.0
DEFAULT_RETRY_SECONDS = 30.0


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _generate(prompt: str, schema: type[BaseModel]) -> tuple[BaseModel, int, int]:
    """Return (parsed response, input tokens, output tokens), or raise RateLimited."""
    if settings.LLM_PROVIDER == OPENAI_COMPATIBLE:
        return _generate_openai_compatible(prompt, schema)
    return _generate_gemini(prompt, schema)


def _generate_gemini(prompt: str, schema: type[BaseModel]) -> tuple[BaseModel, int, int]:
    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
                temperature=0.2,
            ),
        )
    except errors.ClientError as exc:
        if exc.code == 429:
            raise RateLimited(_gemini_retry_after(exc)) from exc
        raise
    usage = response.usage_metadata
    output_tokens = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    parsed = response.parsed if isinstance(response.parsed, schema) else schema.model_validate_json(response.text)
    return parsed, usage.prompt_token_count or 0, output_tokens


def _gemini_retry_after(exc: errors.ClientError) -> float:
    """Seconds Gemini asks us to wait, from its RetryInfo detail when present."""
    match = re.search(r"'retryDelay': '(\d+(?:\.\d+)?)s'", str(exc.details))
    return float(match.group(1)) + 1 if match else DEFAULT_RETRY_SECONDS


def strict_schema(schema: type[BaseModel]) -> dict:
    """The JSON schema in the closed form strict mode requires.

    Every object lists all its properties as required and allows no others;
    fields that are optional in Pydantic already accept null, and fields with
    defaults just have to be sent. Defaults are dropped because strict mode
    does not use them.
    """
    def close(node: dict) -> dict:
        node.pop("default", None)
        if "properties" in node:
            node["required"] = list(node["properties"])
            node["additionalProperties"] = False
        children = [*node.get("properties", {}).values(), *node.get("$defs", {}).values(), *node.get("anyOf", [])]
        if isinstance(node.get("items"), dict):
            children.append(node["items"])
        for child in children:
            close(child)
        return node
    return close(copy.deepcopy(schema.model_json_schema()))


def _generate_openai_compatible(prompt: str, schema: type[BaseModel]) -> tuple[BaseModel, int, int]:
    body = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": schema.__name__.strip("_"),
            "strict": settings.LLM_STRICT_SCHEMA,
            "schema": strict_schema(schema) if settings.LLM_STRICT_SCHEMA else schema.model_json_schema(),
        }},
    }
    if settings.LLM_REASONING_EFFORT:
        body["reasoning_effort"] = settings.LLM_REASONING_EFFORT
    response = httpx.post(f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"}, timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code == 429:
        raise RateLimited(float(response.headers.get("retry-after", DEFAULT_RETRY_SECONDS)) + 1)
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage") or {}
    parsed = schema.model_validate_json(data["choices"][0]["message"]["content"])
    return parsed, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def _throttle() -> None:
    global _last_call
    wait = _last_call + min_interval_seconds - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def generate_json(prompt: str, schema: type[BaseModel], purpose: str, max_wait_seconds: float = 0) -> BaseModel:
    """Call the LLM and return the parsed response. Raises on any provider or parsing error.

    When the provider rate-limits the call (HTTP 429), wait as asked and retry, as long as
    the total wait stays within max_wait_seconds. Interactive requests pass 0 so
    they fall back to basic mode at once; background jobs can afford to wait.
    """
    max_wait_seconds = max(max_wait_seconds, min_wait_seconds)
    waited = 0.0
    while True:
        _throttle()
        try:
            parsed, input_tokens, output_tokens = _generate(prompt, schema)
            break
        except RateLimited as exc:
            if waited + exc.retry_after > max_wait_seconds:
                raise
            logger.warning("LLM rate limit on %s; retrying in %.0fs", purpose, exc.retry_after)
            time.sleep(exc.retry_after)
            waited += exc.retry_after
    parsed = schema.model_validate(_plain(parsed.model_dump()))
    usage_log.record(purpose, input_tokens, output_tokens)
    input_price, output_price = prices()
    logger.info("LLM %s: %d in, %d out tokens (~$%.5f)", purpose, input_tokens, output_tokens,
                input_tokens * input_price + output_tokens * output_price)
    return parsed
