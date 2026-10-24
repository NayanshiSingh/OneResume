"""The LLM client: provider selection, the OpenAI-compatible adapter, and rate-limit handling."""

import json
from typing import Optional

import httpx
import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.config import settings
from app.services import ai_status, jd_analyzer, llm_client

REAL_GENERATE = llm_client._generate  # captured before the autouse fixture blocks live calls


class _Item(BaseModel):
    name: str
    note: Optional[str] = None


class _Answer(BaseModel):
    items: list[_Item] = []
    summary: str


@pytest.fixture
def groq(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://api.groq.com/openai/v1/")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setattr(llm_client, "_generate", REAL_GENERATE)
    sent = []

    def respond_with(response: httpx.Response):
        def fake_post(url, json, headers, timeout):
            sent.append({"url": url, "json": json, "headers": headers})
            return httpx.Response(response.status_code, headers=response.headers, content=response.content,
                                  request=httpx.Request("POST", url))
        monkeypatch.setattr(llm_client.httpx, "post", fake_post)
        return sent
    return respond_with


def _completion(content: dict, prompt_tokens=120, completion_tokens=40) -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    })


class TestOpenAICompatible:
    def test_request_and_parsed_response(self, groq):
        sent = groq(_completion({"items": [{"name": "a", "note": None}], "summary": "ok"}))
        parsed = llm_client.generate_json("Describe it", _Answer, "test")
        assert parsed == _Answer(items=[_Item(name="a")], summary="ok")
        request = sent[0]
        assert request["url"] == "https://api.groq.com/openai/v1/chat/completions"
        assert request["headers"]["Authorization"] == "Bearer test-key"
        body = request["json"]
        assert body["model"] == "openai/gpt-oss-120b" and body["reasoning_effort"] == "low"
        assert body["messages"] == [{"role": "user", "content": "Describe it"}]
        fmt = body["response_format"]["json_schema"]
        assert fmt["strict"] is True and fmt["name"] == "Answer"

    def test_usage_is_recorded(self, groq):
        groq(_completion({"summary": "ok", "items": []}, prompt_tokens=300, completion_tokens=70))
        before = llm_client.usage_log.total
        llm_client.generate_json("p", _Answer, "test")
        after = llm_client.usage_log.total
        assert (after.input_tokens - before.input_tokens, after.output_tokens - before.output_tokens) == (300, 70)

    def test_rate_limit_uses_retry_after_header(self, groq):
        groq(httpx.Response(429, headers={"retry-after": "7"}, json={"error": {"message": "slow down"}}))
        with pytest.raises(llm_client.RateLimited) as exc:
            llm_client.generate_json("p", _Answer, "test")
        assert exc.value.retry_after == 8.0

    def test_server_error_falls_back_to_basic_analysis(self, groq):
        groq(httpx.Response(500, json={"error": {"message": "boom"}}))
        result = jd_analyzer.analyze_jd("Backend Engineer. Requirements: Python and PostgreSQL.")
        assert result.mode == "basic"
        assert any("AI analysis failed" in w for w in result.warnings)

    def test_schema_mismatch_raises(self, groq):
        groq(_completion({"items": []}))  # missing the required summary
        with pytest.raises(ValueError):
            llm_client.generate_json("p", _Answer, "test")

    def test_best_effort_mode_sends_the_plain_schema(self, groq, monkeypatch):
        monkeypatch.setattr(settings, "LLM_STRICT_SCHEMA", False)
        monkeypatch.setattr(settings, "LLM_REASONING_EFFORT", "")
        sent = groq(_completion({"summary": "ok"}))
        llm_client.generate_json("p", _Answer, "test")
        body = sent[0]["json"]
        assert body["response_format"]["json_schema"]["strict"] is False
        assert body["response_format"]["json_schema"]["schema"] == _Answer.model_json_schema()
        assert "reasoning_effort" not in body


def test_strict_schema_closes_every_object():
    schema = llm_client.strict_schema(_Answer)
    item = schema["$defs"]["_Item"]
    assert schema["required"] == ["items", "summary"] and schema["additionalProperties"] is False
    assert item["required"] == ["name", "note"] and item["additionalProperties"] is False
    assert "default" not in json.dumps(schema)
    assert _Answer.model_json_schema()["required"] == ["summary"]  # the model's own schema is untouched


def test_gemini_rate_limit_reads_retry_delay(monkeypatch):
    def limited(**kwargs):
        raise genai_errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota",
                                                       "details": [{"retryDelay": "2s"}]}})
    fake = type("Client", (), {"models": type("Models", (), {"generate_content": staticmethod(limited)})()})()
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake)
    with pytest.raises(llm_client.RateLimited) as exc:
        llm_client._generate_gemini("p", _Answer)
    assert exc.value.retry_after == 3.0


class TestProviderSettings:
    def test_gemini_needs_the_gemini_key(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_API_KEY", "groq-key")
        assert not ai_status.llm_available()
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")
        assert ai_status.status() == {"llm": True, "llm_provider": "Google Gemini", "embeddings": False}

    def test_openai_compatible_needs_its_own_key(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "openai_compatible")
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")
        assert not ai_status.llm_available()
        monkeypatch.setattr(settings, "LLM_API_KEY", "groq-key")
        assert ai_status.status()["llm"] and ai_status.status()["llm_provider"] == "Groq"

    def test_prices_follow_the_provider(self, monkeypatch):
        assert llm_client.prices() == (llm_client.GEMINI_INPUT_PRICE, llm_client.GEMINI_OUTPUT_PRICE)
        monkeypatch.setattr(settings, "LLM_PROVIDER", "openai_compatible")
        assert llm_client.prices() == (0.0, 0.0)
        monkeypatch.setattr(settings, "LLM_INPUT_PRICE_PER_M", 0.15)
        assert llm_client.prices()[0] == pytest.approx(0.15 / 1_000_000)


def test_harness_wait_floor_lets_interactive_calls_wait(monkeypatch):
    calls, sleeps = [], []

    def flaky(prompt, schema):
        calls.append(1)
        if len(calls) == 1:
            raise llm_client.RateLimited(5.0)
        return schema(summary="ok"), 1, 1
    monkeypatch.setattr(llm_client, "_generate", flaky)
    monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
    monkeypatch.setattr(llm_client, "min_wait_seconds", 60.0)
    assert llm_client.generate_json("p", _Answer, "test").summary == "ok"
    assert sleeps == [5.0]


def test_typographic_hyphens_and_spaces_become_plain(monkeypatch):
    # gpt-oss on Groq wrote "end\u2011to\u2011end" and "20\u202fk"; they would not match "end-to-end" or "20k".
    def typographic(prompt, schema):
        return schema(items=[_Item(name="end\u2011to\u2011end tests", note="20\u202fk users")], summary="a\u00a0b"), 1, 1
    monkeypatch.setattr(llm_client, "_generate", typographic)
    parsed = llm_client.generate_json("p", _Answer, "test")
    assert parsed.items[0].name == "end-to-end tests" and parsed.items[0].note == "20 k users"
    assert parsed.summary == "a b"
