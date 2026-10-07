import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional, Protocol
from urllib.parse import urlparse

import anthropic
import openai

from backend.config import Settings
from backend.signals.config import SignalSettings

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5.0
MAX_REASON_WORDS = 25
MAX_OUTPUT_TOKENS = 256

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["take", "skip"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["action", "confidence", "reason"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You review intraday trading alert candidates for a leveraged ETF before they are shown to a trader. The system only alerts; it never places orders.

You receive a JSON snapshot with the signal type, price, precomputed indicator values (session VWAP, fast and slow EMAs, Bollinger Bands, relative volume), and the last bars (OHLCV). The indicators are already computed and correct: do not recompute them. Judge whether this candidate is a high-quality setup worth alerting on, or likely noise (for example a weak cross, an extended move far above the bands, fading volume, or choppy price action around VWAP).

Respond with only a JSON object, no other text:
{"action": "take" or "skip", "confidence": number from 0 to 1, "reason": "at most 25 words"}"""


@dataclass
class FilterDecision:
    action: str  # "take" | "skip" | "unfiltered"
    confidence: Optional[float] = None
    reason: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class LLMProvider(Protocol):
    name: str
    model: str

    async def complete(self, system: str, user: str, timeout: float) -> str: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def complete(self, system: str, user: str, timeout: float) -> str:
        client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=timeout, max_retries=0)
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": DECISION_SCHEMA}},
            )
        finally:
            await client.close()
        return next((b.text for b in response.content if b.type == "text"), "")


class OpenAICompatibleProvider:
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    async def complete(self, system: str, user: str, timeout: float) -> str:
        client = openai.AsyncOpenAI(
            base_url=self.base_url, api_key=self.api_key or "not-needed", timeout=timeout, max_retries=0
        )
        try:
            # Without a cap, OpenRouter reserves the model's full output budget against
            # the account's credit. OpenAI itself names the parameter differently.
            limit = "max_completion_tokens" if self.name == "openai" else "max_tokens"
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                **{limit: MAX_OUTPUT_TOKENS},
            )
        finally:
            await client.close()
        return (response.choices[0].message.content or "") if response.choices else ""


def compat_kind(base_url: str) -> str:
    host = (urlparse(base_url).hostname or "").lower()
    if host.endswith("openrouter.ai"):
        return "openrouter"
    if host.endswith("openai.com"):
        return "openai"
    return "local"


def resolve_provider(app: Settings, signals: SignalSettings) -> Optional[LLMProvider]:
    if app.ai_provider == "anthropic":
        if not app.anthropic_api_key:
            return None
        return AnthropicProvider(app.anthropic_api_key, signals.llm_model_anthropic)

    kind = compat_kind(app.openai_compat_base_url)
    if kind == "local":
        if not app.openai_compat_model:
            return None
        return OpenAICompatibleProvider("local", app.openai_compat_base_url, "", app.openai_compat_model)
    if not app.openai_compat_api_key:
        return None
    model = signals.llm_model_openrouter if kind == "openrouter" else signals.llm_model_openai
    return OpenAICompatibleProvider(kind, app.openai_compat_base_url, app.openai_compat_api_key, model)


def parse_decision(text: str) -> tuple[str, float, str]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {"action", "confidence", "reason"}:
        raise ValueError("unexpected keys")
    action, confidence, reason = data["action"], data["confidence"], data["reason"]
    if action not in ("take", "skip"):
        raise ValueError("invalid action")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("invalid confidence")
    if not isinstance(reason, str):
        raise ValueError("invalid reason")
    return action, float(confidence), " ".join(reason.split()[:MAX_REASON_WORDS])


async def filter_snapshot(
    snapshot: dict, provider: Optional[LLMProvider], timeout: float = TIMEOUT_SECONDS
) -> FilterDecision:
    if provider is None:
        return FilterDecision("unfiltered", reason="No AI provider configured")
    try:
        text = await asyncio.wait_for(
            provider.complete(SYSTEM_PROMPT, json.dumps(snapshot), timeout), timeout=timeout
        )
        action, confidence, reason = parse_decision(text)
        return FilterDecision(action, confidence, reason, provider.name, provider.model)
    except (asyncio.TimeoutError, anthropic.APITimeoutError, openai.APITimeoutError):
        return FilterDecision("unfiltered", reason="LLM timed out", provider=provider.name, model=provider.model)
    except (ValueError, json.JSONDecodeError):
        return FilterDecision("unfiltered", reason="LLM returned invalid JSON", provider=provider.name, model=provider.model)
    except Exception as e:
        # Log the error type only: SDK exception text can echo request details.
        log.warning("LLM filter failed: %s", type(e).__name__)
        return FilterDecision("unfiltered", reason=f"LLM error ({type(e).__name__})", provider=provider.name, model=provider.model)
