from datetime import date, timedelta
from typing import Any, Optional

import httpx

BASE_URL = "https://finnhub.io/api/v1"
TIMEOUT = 15.0
NEWS_DAYS = 7


class FinnhubError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class RateLimited(FinnhubError):
    def __init__(self):
        super().__init__(429, "Finnhub is limiting requests. Try again in a minute.")


class Finnhub:
    def __init__(self, key: str, client: Optional[httpx.AsyncClient] = None):
        self.key = key
        self.client = client

    async def _get(self, endpoint: str, **params: Any) -> Any:
        # The key goes in a header so it's never part of a URL, a log line, or an error.
        headers = {"X-Finnhub-Token": self.key}
        try:
            if self.client is not None:
                response = await self.client.get(f"{BASE_URL}/{endpoint}", params=params, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    response = await client.get(f"{BASE_URL}/{endpoint}", params=params, headers=headers)
        except httpx.HTTPError as e:
            raise FinnhubError(502, f"Finnhub couldn't be reached ({type(e).__name__})") from None
        if response.status_code == 429:
            raise RateLimited()
        if response.status_code in (401, 403):
            raise FinnhubError(response.status_code, f"Finnhub refused {endpoint} (HTTP {response.status_code})")
        if response.status_code != 200:
            raise FinnhubError(502, f"Finnhub returned HTTP {response.status_code} for {endpoint}")
        try:
            return response.json()
        except ValueError:
            raise FinnhubError(502, f"Finnhub sent an invalid reply for {endpoint}") from None

    async def profile(self, ticker: str) -> Optional[dict]:
        data = await self._get("stock/profile2", symbol=ticker)
        # An unknown ticker comes back as an empty object.
        return data if isinstance(data, dict) and data.get("name") else None

    async def quote(self, ticker: str) -> dict:
        data = await self._get("quote", symbol=ticker)
        return data if isinstance(data, dict) else {}

    async def metrics(self, ticker: str) -> tuple[dict, dict]:
        data = await self._get("stock/metric", symbol=ticker, metric="all")
        if not isinstance(data, dict):
            return {}, {}
        metric = data.get("metric") if isinstance(data.get("metric"), dict) else {}
        annual = (data.get("series") or {}).get("annual") if isinstance(data.get("series"), dict) else None
        return metric, annual if isinstance(annual, dict) else {}

    async def peers(self, ticker: str) -> list:
        data = await self._get("stock/peers", symbol=ticker)
        return data if isinstance(data, list) else []

    async def recommendations(self, ticker: str) -> list:
        data = await self._get("stock/recommendation", symbol=ticker)
        return data if isinstance(data, list) else []

    async def news(self, ticker: str, today: date) -> list[dict]:
        data = await self._get("company-news", symbol=ticker, **{"from": (today - timedelta(days=NEWS_DAYS)).isoformat(), "to": today.isoformat()})
        out = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict) or not item.get("headline") or not isinstance(item.get("datetime"), (int, float)):
                continue
            out.append(
                {
                    "time": float(item["datetime"]),
                    "source": item.get("source") or "Finnhub",
                    "headline": str(item["headline"]).strip(),
                    "url": item.get("url") if str(item.get("url", "")).startswith("https://") else None,
                    "provider": "finnhub",
                    "article_id": None,
                }
            )
        return out
