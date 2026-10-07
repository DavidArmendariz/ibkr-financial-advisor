import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.config import Settings
from backend.signals import llm_filter
from backend.signals.config import SignalSettings
from backend.signals.llm_filter import (
    AnthropicProvider,
    OpenAICompatibleProvider,
    filter_snapshot,
    parse_decision,
    resolve_provider,
)

SNAPSHOT = {"symbol": "SOXL", "signal_type": "LONG_ENTRY", "price": 42.15, "indicators": {}, "bars": []}


class FakeProvider:
    name, model = "fake", "fake-model"

    def __init__(self, reply="", delay=0.0, error=None):
        self.reply, self.delay, self.error = reply, delay, error
        self.calls = []

    async def complete(self, system, user, timeout):
        self.calls.append(json.loads(user))
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.reply


async def test_take_decision():
    provider = FakeProvider(json.dumps({"action": "take", "confidence": 0.82, "reason": "Clean VWAP reclaim on volume"}))
    d = await filter_snapshot(SNAPSHOT, provider)
    assert (d.action, d.confidence, d.reason, d.provider, d.model) == ("take", 0.82, "Clean VWAP reclaim on volume", "fake", "fake-model")
    assert provider.calls == [SNAPSHOT]


async def test_skip_decision_in_code_fence():
    d = await filter_snapshot(SNAPSHOT, FakeProvider('```json\n{"action": "skip", "confidence": 0.3, "reason": "Choppy"}\n```'))
    assert (d.action, d.confidence) == ("skip", 0.3)


async def test_timeout_passes_through_unfiltered():
    d = await filter_snapshot(SNAPSHOT, FakeProvider("{}", delay=1.0), timeout=0.05)
    assert d.action == "unfiltered" and "timed out" in d.reason


@pytest.mark.parametrize(
    "reply",
    [
        "not json",
        '{"action": "buy", "confidence": 0.9, "reason": "x"}',
        '{"action": "take", "confidence": 1.4, "reason": "x"}',
        '{"action": "take", "confidence": true, "reason": "x"}',
        '{"action": "take", "confidence": 0.9}',
        '{"action": "take", "confidence": 0.9, "reason": "x", "extra": 1}',
        "[]",
    ],
)
async def test_invalid_json_passes_through_unfiltered(reply):
    d = await filter_snapshot(SNAPSHOT, FakeProvider(reply))
    assert d.action == "unfiltered" and "invalid JSON" in d.reason


async def test_missing_provider_passes_through_unfiltered():
    d = await filter_snapshot(SNAPSHOT, None)
    assert d.action == "unfiltered" and d.provider is None


async def test_provider_error_passes_through_unfiltered():
    d = await filter_snapshot(SNAPSHOT, FakeProvider(error=RuntimeError("boom")))
    assert d.action == "unfiltered" and "RuntimeError" in d.reason


def test_reason_is_capped_at_25_words():
    _, _, reason = parse_decision(json.dumps({"action": "take", "confidence": 0.5, "reason": " ".join(["w"] * 40)}))
    assert len(reason.split()) == 25


# ── Provider resolution reuses the app's AI settings ─────────────────────────


def app(**kw):
    return Settings.model_construct(**{**Settings.model_construct().model_dump(), **kw})


SIG = SignalSettings.model_construct()


def test_resolve_anthropic():
    p = resolve_provider(app(ai_provider="anthropic", anthropic_api_key="sk-ant-test"), SIG)
    assert isinstance(p, AnthropicProvider) and p.model == "claude-haiku-4-5-20251001"
    assert resolve_provider(app(ai_provider="anthropic", anthropic_api_key=""), SIG) is None


@pytest.mark.parametrize(
    "base_url, name, model",
    [
        ("https://openrouter.ai/api/v1", "openrouter", "anthropic/claude-haiku-4.5"),
        ("https://api.openai.com/v1", "openai", "gpt-4.1-mini"),
    ],
)
def test_resolve_hosted_openai_compatible(base_url, name, model):
    settings = app(ai_provider="openai_compatible", openai_compat_base_url=base_url, openai_compat_api_key="k")
    p = resolve_provider(settings, SIG)
    assert (p.name, p.model) == (name, model)
    settings_no_key = app(ai_provider="openai_compatible", openai_compat_base_url=base_url, openai_compat_api_key="")
    assert resolve_provider(settings_no_key, SIG) is None


def test_resolve_local_uses_configured_model_without_key():
    settings = app(ai_provider="openai_compatible", openai_compat_base_url="http://localhost:11434/v1",
                   openai_compat_api_key="", openai_compat_model="llama3.1")
    p = resolve_provider(settings, SIG)
    assert (p.name, p.model) == ("local", "llama3.1")


# ── SDK request shapes (mocked clients) ──────────────────────────────────────


async def test_anthropic_provider_requests_structured_json(monkeypatch):
    captured = {}

    class FakeMessages:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"action":"skip","confidence":0.1,"reason":"r"}')])

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.messages = FakeMessages()

        async def close(self):
            pass

    monkeypatch.setattr(llm_filter.anthropic, "AsyncAnthropic", FakeClient)
    d = await filter_snapshot(SNAPSHOT, AnthropicProvider("sk-ant-test", "claude-haiku-4-5-20251001"))
    assert d.action == "skip"
    assert captured["model"] == "claude-haiku-4-5-20251001"
    assert captured["output_config"]["format"]["schema"]["required"] == ["action", "confidence", "reason"]
    assert captured["client"]["max_retries"] == 0 and captured["client"]["timeout"] == 5.0


async def test_openai_compatible_provider(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            msg = SimpleNamespace(content='{"action":"take","confidence":0.9,"reason":"r"}')
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self):
            pass

    monkeypatch.setattr(llm_filter.openai, "AsyncOpenAI", FakeClient)
    provider = OpenAICompatibleProvider("openrouter", "https://openrouter.ai/api/v1", "k", "anthropic/claude-haiku-4.5")
    d = await filter_snapshot(SNAPSHOT, provider)
    assert (d.action, d.confidence) == ("take", 0.9)
    assert captured["model"] == "anthropic/claude-haiku-4.5"
    assert captured["messages"][0]["role"] == "system"
    assert captured["max_tokens"] == 256
