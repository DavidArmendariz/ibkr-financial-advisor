import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx

from backend.macro.indicators import Indicator, change_fields

log = logging.getLogger(__name__)

# Banco de la República's official USD/COP rate (TRM) on Colombia's open-data
# portal. IBKR doesn't offer the Colombian peso at all.
URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
PARAMS = {"$order": "vigenciadesde DESC", "$limit": "31"}
BOGOTA = ZoneInfo("America/Bogota")
# The TRM changes once a day; it's published in the afternoon for the next business day.
REFRESH_INTERVAL = timedelta(hours=1)
RETRY_INTERVAL = timedelta(minutes=5)
TIMEOUT = 10.0


@dataclass(frozen=True)
class Rate:
    value: float
    valid_from: date
    valid_to: date


def parse_rows(rows: list[dict]) -> list[Rate]:
    rates = [
        Rate(
            float(r["valor"]),
            date.fromisoformat(r["vigenciadesde"][:10]),
            date.fromisoformat(r["vigenciahasta"][:10]),
        )
        for r in rows
    ]
    return sorted(rates, key=lambda r: r.valid_from, reverse=True)


def current(rates: list[Rate], today: date) -> tuple[Optional[Rate], Optional[Rate]]:
    # Rates are newest first; skip one already published for a later day.
    for i, rate in enumerate(rates):
        if rate.valid_from <= today:
            return rate, rates[i + 1] if i + 1 < len(rates) else None
    return None, None


class TrmFeed:
    def __init__(self, ind: Indicator) -> None:
        self.ind = ind
        self.rates: list[Rate] = []
        self.error: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            ok = await self.fetch()
            await asyncio.sleep((REFRESH_INTERVAL if ok else RETRY_INTERVAL).total_seconds())

    async def fetch(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> bool:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, transport=transport) as client:
                resp = await client.get(URL, params=PARAMS)
                resp.raise_for_status()
                rates = parse_rows(resp.json())
            if not rates:
                raise ValueError("no rates returned")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Keep the last rates on screen; the card shows the error next to them.
            self.error = f"Couldn't load the TRM from datos.gov.co: {str(e) or type(e).__name__}"
            log.warning(self.error)
            return False
        self.rates, self.error = rates, None
        return True

    def state(self, now: datetime) -> dict[str, Any]:
        ind = self.ind
        rate, prev = current(self.rates, now.astimezone(BOGOTA).date())
        value = rate.value if rate else None
        prev_value = prev.value if prev else None
        midnight = lambda d: datetime.combine(d, datetime.min.time(), BOGOTA).timestamp()
        history = [r for r in self.rates if rate is None or r.valid_from <= rate.valid_from][:30]
        return {
            "key": ind.key,
            "label": ind.label,
            "unit": ind.unit,
            "change_mode": ind.change_mode,
            "decimals": ind.decimals,
            "contract": "TRM",
            "contract_month": None,
            "value": value,
            "previous_close": prev_value,
            **change_fields(value, prev_value, ind.change_mode),
            "market_open": False,
            "freshness": "daily",
            "valid_from": rate.valid_from.isoformat() if rate else None,
            "valid_to": rate.valid_to.isoformat() if rate else None,
            "updated_at": None,
            # Doesn't depend on IBKR, so an IBKR drop doesn't make it stale.
            "stale": False,
            "error": self.error,
            "sparkline": [{"time": midnight(r.valid_from), "value": r.value} for r in reversed(history)],
        }
