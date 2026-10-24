"""The single place that calls Gemini.

Every call asks for JSON matching a Pydantic schema, uses a low thinking
level to keep cost down, and records token usage so evaluation runs can
report what they actually cost. Tests replace `_generate`.
"""

import logging
from dataclasses import dataclass, field

from google import genai
from google.genai import types
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


def generate_json(prompt: str, schema: type[BaseModel], purpose: str) -> BaseModel:
    """Call Gemini and return the parsed response. Raises on any provider or parsing error."""
    parsed, input_tokens, output_tokens = _generate(prompt, schema)
    usage_log.record(purpose, input_tokens, output_tokens)
    logger.info("Gemini %s: %d in, %d out tokens (~$%.5f)", purpose, input_tokens, output_tokens,
                input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE)
    return parsed
