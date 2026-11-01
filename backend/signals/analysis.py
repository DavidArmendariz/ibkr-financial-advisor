import asyncio
import json
from datetime import datetime, time, timedelta, timezone
from typing import Optional

import anthropic
import openai

from backend.signals.llm_filter import LLMProvider, load_json_reply
from backend.signals.rules import EMA_CROSS, VWAP_BAND_ABOVE, VWAP_CROSS

KINDS = ("pre", "post")
TIMEOUT_SECONDS = 60.0
MAX_OUTPUT_TOKENS = 1500
SESSION_END = time(20, 0)  # after-hours end, so a day's request covers every bar
MIN_MINUTES_AFTER = 15
HORIZONS = (15, 30, 60)
CONTEXT_BAR_SECONDS = 300
LONG_TRIGGERS = {EMA_CROSS, VWAP_CROSS, VWAP_BAND_ABOVE, "LONG_ENTRY"}

PRE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["take", "skip"]},
        "confidence": {"type": "number"},
        "case_for": {"type": "string"},
        "risks": {"type": "string"},
        "invalidation": {"type": "string"},
    },
    "required": ["action", "confidence", "case_for", "risks", "invalidation"],
    "additionalProperties": False,
}

POST_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["good", "bad", "mixed"]},
        "explanation": {"type": "string"},
    },
    "required": ["verdict", "explanation"],
    "additionalProperties": False,
}

PRE_PROMPT = """You analyze an intraday alert on a leveraged ETF as if it were that moment. You receive the signal, the indicators, recent 1-minute bars, and 5-minute bars for the session so far. That is all that was known then: do not use or guess anything from later, and don't rely on outside knowledge of that date. Don't recompute the indicators. Stick to the data given. The app only alerts and never places orders, so give no order sizes.

Respond with only a JSON object, no other text:
{"action": "take" or "skip", "confidence": number from 0 to 1, "case_for": "the case for acting, at most 60 words", "risks": "what could go wrong, at most 60 words", "invalidation": "what would prove the idea wrong, at most 40 words"}"""

POST_PROMPT = """You judge, with hindsight, whether acting on an intraday alert on a leveraged ETF was a good idea. You receive the signal, the bars for the session, and outcome figures in percent. The figures are computed and correct: use them as given, and never recalculate them. "directions" lists the entries to judge: if it holds both long and short, the alert implied no direction, so cover how each would have done. Judge the entry, not just the result: a sound setup can lose, and luck can win. The app only alerts and never places orders.

Respond with only a JSON object, no other text:
{"verdict": "good", "bad" or "mixed", "explanation": "what happened and why, at most 120 words"}"""


class AnalysisError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _closes_at(bar: dict) -> float:
    return bar["time"] + 60


def bars_known_at(bars: list[dict], signal_time: datetime) -> list[dict]:
    limit = signal_time.timestamp()
    return [b for b in bars if _closes_at(b) <= limit]


def bars_after(bars: list[dict], signal_time: datetime, close_time: datetime) -> list[dict]:
    start, end = signal_time.timestamp(), close_time.timestamp()
    return [b for b in bars if start < _closes_at(b) <= end]


def check_post_mortem_ready(signal_time: datetime, close_time: datetime, now: datetime) -> None:
    earliest = signal_time + timedelta(minutes=MIN_MINUTES_AFTER)
    if earliest > close_time:
        raise AnalysisError(409, f"Fewer than {MIN_MINUTES_AFTER} minutes remained in the session after this signal")
    if now < earliest:
        raise AnalysisError(409, f"Too soon: wait until {MIN_MINUTES_AFTER} minutes after the signal")


def directions_for(signal_type: str) -> list[str]:
    return ["long"] if signal_type in LONG_TRIGGERS else ["long", "short"]


def _percent(price: float, entry: float) -> float:
    return (price / entry - 1) * 100


def outcomes(later: list[dict], entry: float, signal_time: datetime, close_time: datetime) -> dict:
    start, end = signal_time.timestamp(), close_time.timestamp()

    def return_at(target: float) -> Optional[float]:
        if target > end:
            return None
        reached = [b for b in later if _closes_at(b) <= target]
        return _percent(reached[-1]["close"], entry) if reached else None

    return {
        "return_pct": {
            **{f"{m}m": return_at(start + m * 60) for m in HORIZONS},
            "close": _percent(later[-1]["close"], entry) if later else None,
        },
        "largest_gain_pct": _percent(max(b["high"] for b in later), entry) if later else None,
        "largest_loss_pct": _percent(min(b["low"] for b in later), entry) if later else None,
        "returned_to_start": any(b["low"] <= entry <= b["high"] for b in later),
    }


def context_bars(bars: list[dict]) -> list[list]:
    # A session of 1-minute bars is about 1,000 rows per click; 5-minute bars keep
    # the shape of the day at a fraction of the cost.
    buckets: dict[int, list[dict]] = {}
    for bar in bars:
        buckets.setdefault(int(bar["time"]) // CONTEXT_BAR_SECONDS, []).append(bar)
    return [
        [
            datetime.fromtimestamp(bucket * CONTEXT_BAR_SECONDS, timezone.utc).isoformat(),
            group[0]["open"],
            max(b["high"] for b in group),
            min(b["low"] for b in group),
            group[-1]["close"],
            sum(b["volume"] for b in group),
        ]
        for bucket, group in sorted(buckets.items())
    ]


def signal_facts(signal: dict) -> dict:
    keys = ("symbol", "signal_type", "category", "time", "price", "indicators", "ema_periods", "bars")
    return {k: signal[k] for k in keys if k in signal}


def pre_request(signal: dict, bars: list[dict]) -> dict:
    known = bars_known_at(bars, datetime.fromisoformat(signal["time"]))
    return {"signal": signal_facts(signal), "session_bars_5min_time_ohlcv": context_bars(known)}


def post_request(signal: dict, bars: list[dict], figures: dict) -> dict:
    return {
        "signal": signal_facts(signal),
        "session_bars_5min_time_ohlcv": context_bars(bars),
        "directions": directions_for(signal["signal_type"]),
        "outcome_for_a_long_entry_percent": figures,
    }


def parse_pre(text: str) -> dict:
    data = load_json_reply(text)
    if not isinstance(data, dict) or set(data) != set(PRE_SCHEMA["required"]):
        raise ValueError("unexpected keys")
    confidence = data["confidence"]
    if data["action"] not in ("take", "skip"):
        raise ValueError("invalid action")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("invalid confidence")
    if not all(isinstance(data[k], str) and data[k].strip() for k in ("case_for", "risks", "invalidation")):
        raise ValueError("invalid text")
    return data


def parse_post(text: str) -> dict:
    data = load_json_reply(text)
    if not isinstance(data, dict) or set(data) != set(POST_SCHEMA["required"]):
        raise ValueError("unexpected keys")
    if data["verdict"] not in ("good", "bad", "mixed"):
        raise ValueError("invalid verdict")
    if not isinstance(data["explanation"], str) or not data["explanation"].strip():
        raise ValueError("invalid text")
    return data


async def _ask(provider: LLMProvider, prompt: str, request: dict, schema: dict) -> str:
    try:
        return await asyncio.wait_for(
            provider.complete(prompt, json.dumps(request), TIMEOUT_SECONDS, max_tokens=MAX_OUTPUT_TOKENS, schema=schema),
            timeout=TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, anthropic.APITimeoutError, openai.APITimeoutError):
        raise AnalysisError(504, "The AI provider timed out after 60 seconds")
    except AnalysisError:
        raise
    except Exception as e:
        # The type only: SDK exception text can echo request details.
        raise AnalysisError(502, f"The AI provider failed ({type(e).__name__})")


async def run(kind: str, signal: dict, bars: list[dict], close_time: datetime, provider: LLMProvider) -> dict:
    signal_time = datetime.fromisoformat(signal["time"])
    try:
        if kind == "pre":
            return parse_pre(await _ask(provider, PRE_PROMPT, pre_request(signal, bars), PRE_SCHEMA))
        later = bars_after(bars, signal_time, close_time)
        if not later:
            raise AnalysisError(502, "IBKR returned no bars after this signal")
        figures = outcomes(later, signal["price"], signal_time, close_time)
        request = post_request(signal, bars, figures)
        reply = parse_post(await _ask(provider, POST_PROMPT, request, POST_SCHEMA))
        return {**reply, "directions": request["directions"], "outcomes": figures, "hindsight": True}
    except (ValueError, json.JSONDecodeError, KeyError):
        raise AnalysisError(502, "The AI provider returned an invalid reply")
