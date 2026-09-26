from typing import AsyncGenerator

import anthropic
import openai

from backend.config import Settings, get_settings


def _build_system_prompt(portfolio: dict) -> str:
    positions = portfolio.get("positions", [])
    summary = portfolio.get("summary", {})

    positions_text = "\n".join(
        f"  • {p['symbol']} ({p['asset_class']}): {p['quantity']} units "
        f"@ avg ${p['avg_cost']:.2f}, current ${p['market_price']:.2f}, "
        f"P&L: ${p['unrealized_pnl']:+.2f}"
        for p in positions
    ) or "  No open positions."

    return f"""You are an expert AI financial advisor with real-time access to the user's Interactive Brokers portfolio. Your role is to provide thoughtful, personalized analysis and guidance based on their actual holdings.

═══ LIVE PORTFOLIO SNAPSHOT ═══
Net Liquidation Value : ${summary.get('NetLiquidation', 0):>12,.2f}
Unrealized P&L        : ${summary.get('UnrealizedPnL', 0):>+12,.2f}
Realized P&L          : ${summary.get('RealizedPnL', 0):>+12,.2f}
Buying Power          : ${summary.get('BuyingPower', 0):>12,.2f}
Total Cash            : ${summary.get('TotalCashValue', 0):>12,.2f}

Open Positions:
{positions_text}
════════════════════════════════

Guidelines:
- Reference specific positions, quantities, and P&L values when relevant.
- Be concise but thorough. Use markdown formatting for clarity.
- Flag potential risks (concentration, sector exposure, unrealized losses).
- Always note that your analysis is for educational purposes and does not constitute professional financial advice.
- Do not recommend specific buy/sell actions without thorough risk analysis."""


async def stream_chat_response(
    messages: list[dict],
    portfolio: dict,
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    system_prompt = _build_system_prompt(portfolio)

    if settings.ai_provider == "openai_compatible":
        stream = _stream_openai_compatible(settings, system_prompt, messages)
    else:
        stream = _stream_anthropic(settings, system_prompt, messages)

    async for text in stream:
        yield text


async def _stream_anthropic(
    settings: Settings, system_prompt: str, messages: list[dict]
) -> AsyncGenerator[str, None]:
    if not settings.anthropic_api_key:
        raise RuntimeError("No Anthropic API key configured. Add one in Settings.")
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


def openai_compatible_client(base_url: str, api_key: str) -> openai.AsyncOpenAI:
    # Local servers (Ollama, LM Studio) need no key, but the SDK requires one
    return openai.AsyncOpenAI(base_url=base_url, api_key=api_key or "not-needed")


async def _stream_openai_compatible(
    settings: Settings, system_prompt: str, messages: list[dict]
) -> AsyncGenerator[str, None]:
    if not settings.openai_compat_model:
        raise RuntimeError("No model configured for the OpenAI-compatible provider. Set one in Settings.")
    client = openai_compatible_client(settings.openai_compat_base_url, settings.openai_compat_api_key)

    # No max_tokens: providers disagree on the parameter name
    # (max_tokens vs max_completion_tokens), so use each model's default.
    stream = await client.chat.completions.create(
        model=settings.openai_compat_model,
        messages=[{"role": "system", "content": system_prompt}, *messages],
        stream=True,
    )
    async with stream:
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
