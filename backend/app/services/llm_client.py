"""The single place that calls Gemini.

Every call asks for JSON matching a Pydantic schema, uses a low thinking
level to keep cost down, and records token usage so evaluation runs can
report what they actually cost. Tests replace `_generate`.
"""

import logging
import re
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

# USD per token for gemini-3-flash-preview (paid tier, checked 2026-10-24).
INPUT_PRICE = 0.50 / 1_000_000
OUTPUT_PRICE = 3.00 / 1_000_000  # includes thinking tokens


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        return self.input_tokens * INPUT_PRICE + self.output_tokens * OUTPUT_PRICE

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
DEFAULT_RETRY_SECONDS = 30.0


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _generate(prompt: str, schema: type[BaseModel]) -> tuple[BaseModel, int, int]:
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
    usage = response.usage_metadata
    output_tokens = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    parsed = response.parsed if isinstance(response.parsed, schema) else schema.model_validate_json(response.text)
    return parsed, usage.prompt_token_count or 0, output_tokens


def _retry_after(exc: errors.ClientError) -> float:
    """Seconds Gemini asks us to wait, from its RetryInfo detail when present."""
    match = re.search(r"'retryDelay': '(\d+(?:\.\d+)?)s'", str(exc.details))
    return float(match.group(1)) + 1 if match else DEFAULT_RETRY_SECONDS


def _throttle() -> None:
    global _last_call
    wait = _last_call + min_interval_seconds - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def generate_json(prompt: str, schema: type[BaseModel], purpose: str, max_wait_seconds: float = 0) -> BaseModel:
    """Call Gemini and return the parsed response. Raises on any provider or parsing error.

    When Gemini rate-limits the call (HTTP 429), wait as asked and retry, as long as
    the total wait stays within max_wait_seconds. Interactive requests pass 0 so
    they fall back to basic mode at once; background jobs can afford to wait.
    """
    waited = 0.0
    while True:
        _throttle()
        try:
            parsed, input_tokens, output_tokens = _generate(prompt, schema)
            break
        except errors.ClientError as exc:
            delay = _retry_after(exc)
            if exc.code != 429 or waited + delay > max_wait_seconds:
                raise
            logger.warning("Gemini rate limit on %s; retrying in %.0fs", purpose, delay)
            time.sleep(delay)
            waited += delay
    usage_log.record(purpose, input_tokens, output_tokens)
    logger.info("Gemini %s: %d in, %d out tokens (~$%.5f)", purpose, input_tokens, output_tokens,
                input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE)
    return parsed
