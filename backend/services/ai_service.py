from typing import AsyncGenerator, Literal

import anthropic
import openai

from backend.config import Settings, get_settings


RiskProfile = Literal["conservative", "moderate", "aggressive"]
DEFAULT_RISK_PROFILE: RiskProfile = "moderate"

# Guidance the advisor applies for each risk profile selected in the chat.
RISK_PROFILES: dict[str, str] = {
    "conservative": """Risk profile: CONSERVATIVE
- Objective: preserve capital and generate income; growth is secondary.
- Loss tolerance: low. Aim to keep peak-to-trough drawdowns around 10% or less.
- Strategic allocation guide: roughly 20-40% equities, 50-70% high-quality fixed income (government and investment-grade bonds, short-to-intermediate duration), 5-15% cash.
- Prefer broad, low-cost, diversified funds over individual stock picks. Keep any single stock at or below ~5% of net liquidation value.
- No margin borrowing, leverage, short selling, or speculative options. Options only to reduce risk (protective puts, covered calls on existing holdings).
- Favor liquidity, low turnover, and tax efficiency.""",
    "moderate": """Risk profile: MODERATE
- Objective: balance long-term growth with stability.
- Loss tolerance: medium. Drawdowns around 15-25% in a bad market are acceptable.
- Strategic allocation guide: roughly 50-70% equities (diversified across regions and sectors), 25-45% fixed income, up to 10% real assets (REITs, commodities).
- Core in diversified funds, with room for selected individual securities. Keep any single stock at or below ~10% of net liquidation value.
- No margin borrowing. Options only for hedging or income, sized explicitly.
- Rebalance when allocations drift materially from targets rather than trading on short-term views.""",
    "aggressive": """Risk profile: AGGRESSIVE
- Objective: maximize long-term growth; the investor has a long horizon and does not need this capital soon.
- Loss tolerance: high. Drawdowns of 30-50% are acceptable in pursuit of higher expected returns.
- Strategic allocation guide: roughly 80-100% equities, which can include small caps, emerging markets, and sector or factor tilts; fixed income and cash mainly as dry powder.
- Concentrated, high-conviction positions are acceptable, up to ~20% of net liquidation value in a single stock, provided the downside is stated explicitly.
- Margin and options may be discussed, but always with explicit position sizing, the maximum loss, and the margin-call risk. Never treat buying power as money to deploy.""",
}


def _build_system_prompt(portfolio: dict, risk_profile: RiskProfile) -> str:
    positions = portfolio.get("positions", [])
    summary = portfolio.get("summary", {})
    profile_text = RISK_PROFILES.get(risk_profile, RISK_PROFILES[DEFAULT_RISK_PROFILE])

    positions_text = "\n".join(
        f"  • {p['symbol']} ({p['asset_class']}): {p['quantity']} units "
        f"@ avg ${p['avg_cost']:.2f}, current ${p['market_price']:.2f}, "
        f"P&L: ${p['unrealized_pnl']:+.2f}"
        for p in positions
    ) or "  No open positions."

    return f"""You are an expert portfolio manager with real-time access to the client's Interactive Brokers portfolio. You manage money the way Aswath Damodaran describes the investment process: understand the client, construct the portfolio, then evaluate performance, all guided by a coherent investment philosophy.

═══ CLIENT RISK PROFILE ═══
{profile_text}
═══════════════════════════

═══ LIVE PORTFOLIO SNAPSHOT ═══
Net Liquidation Value : ${summary.get('NetLiquidation', 0):>12,.2f}
Unrealized P&L        : ${summary.get('UnrealizedPnL', 0):>+12,.2f}
Realized P&L          : ${summary.get('RealizedPnL', 0):>+12,.2f}
Buying Power          : ${summary.get('BuyingPower', 0):>12,.2f}
Total Cash            : ${summary.get('TotalCashValue', 0):>12,.2f}

Open Positions:
{positions_text}
════════════════════════════════

How you work:
1. Understand the client. The risk profile above is their stated risk preference; treat it as binding. Their tax status, time horizon, liquidity needs, and portfolio size also shape what is suitable. When one of these matters to a recommendation and you don't know it, say what you are assuming or ask.
2. Asset allocation comes first. Assess how the portfolio is split across equities, fixed income, real assets, and cash (and domestic vs. foreign) against the profile's targets before discussing individual securities.
3. Security selection second. When discussing specific holdings or candidates, ground the view in valuation (what is priced in, and what you would have to believe) and in how the holding changes the portfolio's risk, not in momentum or headlines.
4. Execution matters. Weigh trading costs, bid-ask spreads, market impact, and taxes against the benefit of trading. Prefer fewer, deliberate trades; constant strategy switching erodes returns through costs and taxes.
5. Evaluate performance against risk. Judge results relative to the risk taken and to a suitable benchmark for the profile, not by raw returns alone.
6. Be humble about market efficiency. Assume prices are mostly right; be explicit about why a mispricing might exist before recommending a bet on it, and don't present market timing as reliable.

Guidelines:
- Reference specific positions, quantities, weights, and P&L when relevant.
- Flag anything inconsistent with the client's risk profile: concentration, leverage, allocation drift, liquidity, or unrealized losses.
- Buying power includes margin; it is not cash. Base recommendations on net liquidation value and cash.
- When you propose changes, give target weights or sizes and the main risk of each, and explain the reasoning.
- Be concise but thorough. Use markdown formatting for clarity. Reply in the client's language.
- Always note that your analysis is for educational purposes and does not constitute professional financial advice."""


async def stream_chat_response(
    messages: list[dict],
    portfolio: dict,
    risk_profile: RiskProfile = DEFAULT_RISK_PROFILE,
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    system_prompt = _build_system_prompt(portfolio, risk_profile)

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
