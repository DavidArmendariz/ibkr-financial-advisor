from typing import AsyncGenerator
import anthropic
from backend.config import get_settings


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
    if not settings.anthropic_api_key:
        raise RuntimeError("No Anthropic API key configured. Add one in Settings.")
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    system_prompt = _build_system_prompt(portfolio)

    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
