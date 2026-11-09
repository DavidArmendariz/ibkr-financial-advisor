import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend import database
from backend.calendar_events.config import get_calendar_settings
from backend.config import get_settings
from backend.database import FundamentalsAnalysis
from backend.fundamentals import calc, news
from backend.fundamentals.analysis import WriteUpError, write_up
from backend.fundamentals.finnhub import Finnhub, FinnhubError
from backend.services import ibkr_service
from backend.signals.config import get_signal_settings
from backend.signals.llm_filter import resolve_provider
from backend.signals.sessions import ET

log = logging.getLogger(__name__)

CACHE_FOR = timedelta(hours=1)
PEER_CONCURRENCY = 4


class FundamentalsError(Exception):
    def __init__(self, status: int, message: str, code: str = "error"):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class FundamentalsService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[datetime, dict]] = {}
        self._writing: set[str] = set()

    def _client(self) -> Finnhub:
        key = get_calendar_settings().finnhub_api_key
        if not key:
            raise FundamentalsError(400, "Fundamentals need the Finnhub key saved in Calendar settings.", "no_key")
        return Finnhub(key)

    async def lookup(self, raw: str, refresh: bool = False, now: Optional[datetime] = None) -> dict:
        ticker = calc.clean_ticker(raw)
        if ticker is None:
            raise FundamentalsError(422, "Enter a ticker of up to 10 letters, digits, dots, or dashes.", "bad_ticker")
        now = now or datetime.now(timezone.utc)
        cached = self._cache.get(ticker)
        if cached and not refresh and now - cached[0] < CACHE_FOR:
            data = cached[1]
        else:
            data = await self._fetch(ticker, now)
            self._cache[ticker] = (now, data)
        return {**data, "analysis": await self.saved_analysis(ticker)}

    async def _fetch(self, ticker: str, now: datetime) -> dict:
        fh = self._client()
        try:
            profile = await fh.profile(ticker)
            if profile is None:
                raise FundamentalsError(404, f"No US stock was found for {ticker}.", "not_found")
            (metric, series), quote, peers, recs, fh_news = await asyncio.gather(
                fh.metrics(ticker), fh.quote(ticker), fh.peers(ticker), fh.recommendations(ticker),
                fh.news(ticker, now.astimezone(ET).date()),
            )
            peer_list = calc.clean_peers(ticker, peers)
            peer_metrics = await self._peer_metrics(fh, peer_list)
        except FinnhubError as e:
            raise FundamentalsError(e.status, e.message, "rate_limited" if e.status == 429 else "finnhub")
        ib_news, notes = await self._ibkr_news(ticker)
        price = quote.get("c") if isinstance(quote.get("c"), (int, float)) and quote.get("c") else None
        return {
            "ticker": ticker,
            "name": profile.get("name"),
            "industry": profile.get("finnhubIndustry"),
            "exchange": profile.get("exchange"),
            "currency": profile.get("currency"),
            "price": price,
            "change_pct": quote.get("dp") if price is not None else None,
            "market_cap_millions": profile.get("marketCapitalization"),
            "multiples": calc.compare(metric, series, list(peer_metrics.values())),
            "quality": calc.quality(metric),
            "peers": peer_list,
            "ratings": calc.ratings(recs),
            "news": news.merge(fh_news, ib_news),
            "news_notes": notes,
            "fetched_at": now.isoformat(),
        }

    async def _peer_metrics(self, fh: Finnhub, peers: list[str]) -> dict[str, dict]:
        gate = asyncio.Semaphore(PEER_CONCURRENCY)

        async def one(peer: str) -> tuple[str, dict]:
            async with gate:
                metric, _ = await fh.metrics(peer)
                return peer, metric

        return dict(await asyncio.gather(*(one(p) for p in peers)))

    async def _ibkr_news(self, ticker: str) -> tuple[list[dict], list[str]]:
        if not ibkr_service.get_status()["connected"]:
            return [], ["IBKR news needs a connection to TWS."]
        try:
            return await news.ibkr_news(ticker), []
        except asyncio.TimeoutError:
            return [], ["IBKR didn't send news in time."]
        except Exception as e:
            log.warning("IBKR news: %s", type(e).__name__)
            return [], ["IBKR news couldn't be read."]

    async def article(self, provider: str, article_id: str) -> Optional[str]:
        if not ibkr_service.get_status()["connected"]:
            raise FundamentalsError(503, "Not connected to IBKR")
        try:
            return await news.ibkr_article(provider, article_id)
        except asyncio.TimeoutError:
            raise FundamentalsError(504, "IBKR didn't send the article in time")

    async def saved_analysis(self, ticker: str) -> Optional[dict]:
        async with database.AsyncSessionLocal() as session:
            row = await session.get(FundamentalsAnalysis, ticker)
        return self._record(row) if row else None

    @staticmethod
    def _record(row: FundamentalsAnalysis) -> dict:
        return {
            "created_at": _utc(row.created_at).isoformat(),
            "data_time": _utc(row.data_time).isoformat(),
            "provider": row.provider,
            "model": row.model,
            **json.loads(row.result),
        }

    async def analyze(self, raw: str) -> dict:
        ticker = calc.clean_ticker(raw)
        if ticker is None:
            raise FundamentalsError(422, "Enter a valid ticker.", "bad_ticker")
        provider = resolve_provider(get_settings(), get_signal_settings())
        if provider is None:
            raise FundamentalsError(400, "No AI provider is configured. Add one in Settings.", "no_provider")
        if ticker in self._writing:
            raise FundamentalsError(409, "A write-up for this ticker is already running")
        self._writing.add(ticker)
        try:
            data = await self.lookup(ticker)
            try:
                result = await write_up(data, provider)
            except WriteUpError as e:
                raise FundamentalsError(e.status, e.message)
            async with database.AsyncSessionLocal() as session:
                saved = await session.merge(
                    FundamentalsAnalysis(
                        ticker=ticker,
                        created_at=datetime.now(timezone.utc),
                        data_time=datetime.fromisoformat(data["fetched_at"]),
                        provider=provider.name,
                        model=provider.model,
                        result=json.dumps(result),
                    )
                )
                await session.commit()
                return self._record(saved)
        finally:
            self._writing.discard(ticker)


fundamentals_service = FundamentalsService()
