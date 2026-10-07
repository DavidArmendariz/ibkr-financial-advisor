import argparse
import asyncio
import csv
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from backend.config import get_settings
from backend.signals.config import SignalSettings, get_signal_settings
from backend.signals.llm_filter import filter_snapshot, resolve_provider
from backend.signals.models import Bar
from backend.signals.pipeline import Candidate, SignalPipeline
from backend.signals.sessions import ET, SessionCalendar

REPLAY_CLIENT_ID_OFFSET = 50


def parse_time(value: str) -> datetime:
    value = value.strip()
    if value.replace(".", "", 1).isdigit():
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    t = datetime.fromisoformat(value)
    return t if t.tzinfo else t.replace(tzinfo=ET)


def load_csv(path: Path) -> list[Bar]:
    with path.open(newline="") as f:
        rows = csv.DictReader(f)
        return [
            Bar(parse_time(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
            for r in rows
        ]


async def fetch_session(settings: SignalSettings, day: date) -> list[Bar]:
    from ib_async import IB, Stock

    app = get_settings()
    ib = IB()
    port = app.ibkr_paper_port
    await ib.connectAsync(app.ibkr_host, port, clientId=app.ibkr_client_id + REPLAY_CLIENT_ID_OFFSET, timeout=10, readonly=True)
    try:
        contract = Stock(settings.symbol, "SMART", "USD")
        await ib.qualifyContractsAsync(contract)
        warmup_sessions = math.ceil(settings.warmup_bars() * settings.timeframe_minutes / 390) + 1
        end = datetime.combine(day, datetime.min.time(), ET).replace(hour=20)
        bar_size = "1 min" if settings.timeframe_minutes == 1 else f"{settings.timeframe_minutes} mins"
        bars = await ib.reqHistoricalDataAsync(
            contract,
            end.astimezone(timezone.utc),
            f"{warmup_sessions + 3} D",
            bar_size,
            "TRADES",
            not settings.include_premarket,
            formatDate=2,
        )
        return [Bar(b.date, b.open, b.high, b.low, b.close, float(b.volume)) for b in bars]
    finally:
        ib.disconnect()


def replay(bars: Iterable[Bar], settings: SignalSettings, only_day: Optional[date] = None) -> list[Candidate]:
    pipeline = SignalPipeline(settings, SessionCalendar())
    found = []
    for bar in bars:
        emit = only_day is None or bar.time.astimezone(ET).date() == only_day
        found.extend(pipeline.on_bar(bar, emit=emit))
    return found


def format_candidate(c: Candidate) -> str:
    i = c.indicators
    return (
        f"{c.time.astimezone(ET):%Y-%m-%d %H:%M} ET  {c.signal_type} @ {c.price:.2f}  "
        f"VWAP {i.vwap:.2f}  EMA fast {i.ema_fast:.2f} / slow {i.ema_slow:.2f}  "
        f"BB {i.bb_lower:.2f}-{i.bb_upper:.2f}  RVOL {i.rvol:.2f}x"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Replay historical bars through the signal pipeline.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path, help="CSV with time,open,high,low,close,volume (time: ISO or epoch)")
    source.add_argument("--date", type=date.fromisoformat, help="Session to fetch from IBKR (YYYY-MM-DD)")
    parser.add_argument("--timeframe", type=int, help="Bar size in minutes (default: saved setting)")
    parser.add_argument("--llm", action="store_true", help="Also run each signal through the LLM filter")
    args = parser.parse_args()

    settings = get_signal_settings()
    if args.timeframe:
        settings = settings.model_copy(update={"timeframe_minutes": args.timeframe})

    if args.csv:
        bars, only_day = load_csv(args.csv), None
    else:
        bars, only_day = await fetch_session(settings, args.date), args.date
    if not bars:
        print("No bars to replay.")
        return

    candidates = replay(bars, settings, only_day)
    first, last = bars[0].time.astimezone(ET), bars[-1].time.astimezone(ET)
    print(f"Replayed {len(bars)} bars ({first:%Y-%m-%d %H:%M} to {last:%Y-%m-%d %H:%M} ET): {len(candidates)} signal(s)\n")
    provider = resolve_provider(get_settings(), settings) if args.llm else None
    for c in candidates:
        print(format_candidate(c))
        if args.llm:
            d = await filter_snapshot(c.snapshot(), provider)
            conf = f" ({d.confidence:.2f})" if d.confidence is not None else ""
            print(f"    LLM: {d.action}{conf} {d.reason}")


if __name__ == "__main__":
    asyncio.run(main())
