import asyncio
import json

import anthropic
import openai

from backend.signals.llm_filter import LLMProvider, load_json_reply

TIMEOUT_SECONDS = 60.0
MAX_OUTPUT_TOKENS = 1500
MAX_HEADLINES = 15
FIELDS = ("bull_case", "bear_case", "valuation_view", "watch")

SCHEMA = {
    "type": "object",
    "properties": {f: {"type": "string"} for f in FIELDS},
    "required": list(FIELDS),
    "additionalProperties": False,
}

PROMPT = """You review a US stock's fundamentals for an individual investor. You receive its valuation multiples, each compared with the median of its peers and with its own 5-fiscal-year median, quality and growth figures, analyst rating counts for the last two months, and recent headlines. The figures are computed and correct: use them as given and never recalculate them. A null figure is unavailable; say so rather than guessing. Base the review on the data given, not on outside knowledge of the company or of later events. Don't give a buy or sell recommendation, a price target, or position sizes.

Respond with only a JSON object, no other text:
{"bull_case": "the strongest case for the stock, at most 80 words", "bear_case": "the strongest case against, at most 80 words", "valuation_view": "whether it looks cheap or expensive against peers and its own history, and why that may be justified, at most 80 words", "watch": "what to watch next, such as figures or events that would change the view, at most 50 words"}"""


class WriteUpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def request(lookup: dict) -> dict:
    # Only the stock's public figures and headlines: no account, positions, or orders.
    keys = ("ticker", "name", "industry", "currency", "price", "market_cap_millions", "multiples", "quality", "peers", "ratings")
    out = {k: lookup.get(k) for k in keys}
    out["headlines"] = [
        {"time": n["time"], "source": n["source"], "headline": n["headline"]} for n in lookup.get("news", [])[:MAX_HEADLINES]
    ]
    return out


def parse(text: str) -> dict:
    data = load_json_reply(text)
    if not isinstance(data, dict) or set(data) != set(FIELDS):
        raise ValueError("unexpected keys")
    if not all(isinstance(data[f], str) and data[f].strip() for f in FIELDS):
        raise ValueError("invalid text")
    return {f: data[f].strip() for f in FIELDS}


async def write_up(lookup: dict, provider: LLMProvider) -> dict:
    try:
        text = await asyncio.wait_for(
            provider.complete(PROMPT, json.dumps(request(lookup)), TIMEOUT_SECONDS, max_tokens=MAX_OUTPUT_TOKENS, schema=SCHEMA),
            timeout=TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, anthropic.APITimeoutError, openai.APITimeoutError):
        raise WriteUpError(504, "The AI provider timed out after 60 seconds")
    except Exception as e:
        # The type only: SDK exception text can echo request details.
        raise WriteUpError(502, f"The AI provider failed ({type(e).__name__})")
    try:
        return parse(text)
    except (ValueError, json.JSONDecodeError):
        raise WriteUpError(502, "The AI provider returned an invalid reply")
