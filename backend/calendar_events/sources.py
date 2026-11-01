import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

ET = ZoneInfo("US/Eastern")
TIMEOUT = 15.0
FRED_URL = "https://api.stlouisfed.org/fred/release/dates"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FINNHUB_URL = "https://finnhub.io/api/v1/calendar/earnings"
FETCH_DAYS = 45
FOMC_TIME = time(14, 0)
HIGH, MEDIUM = "high", "medium"
TIMINGS = {"bmo": "before_open", "amc": "after_close"}
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}

# FRED gives dates only, so each release's usual time lives here.
RELEASES = {
    10: ("CPI", HIGH, time(8, 30)),
    50: ("Jobs report", HIGH, time(8, 30)),
    46: ("PPI", MEDIUM, time(8, 30)),
    53: ("GDP", MEDIUM, time(8, 30)),
    54: ("PCE", MEDIUM, time(8, 30)),
    9: ("Retail sales", MEDIUM, time(8, 30)),
}


class SourceError(Exception):
    pass


@dataclass(frozen=True)
class Event:
    id: str
    source: str
    name: str
    category: str  # economic | earnings
    importance: str
    day: date
    at: Optional[datetime] = None  # UTC; None when the time isn't known
    timing: Optional[str] = None  # before_open | after_close


def _at(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, ET).astimezone(timezone.utc)


def parse_fred(release_id: int, payload: dict, today: date) -> list[Event]:
    name, importance, clock = RELEASES[release_id]
    days = sorted({date.fromisoformat(r["date"]) for r in payload.get("release_dates", [])})
    return [
        Event(f"fred:{release_id}:{day}", "fred", name, "economic", importance, day, _at(day, clock))
        for day in days
        if day >= today
    ]


def parse_fomc(html: str, today: date) -> list[Event]:
    events = []
    # Each year's panel starts with its heading; the month and date cells follow it.
    years = re.split(r"(\d{4}) FOMC Meetings", html)
    for year_text, panel in zip(years[1::2], years[2::2]):
        year = int(year_text)
        cells = re.findall(
            r'fomc-meeting__month[^>]*>\s*<strong>([A-Za-z/]+)</strong>.*?fomc-meeting__date[^>]*>\s*(\d+)(?:-(\d+))?',
            panel,
            re.S,
        )
        for months, first, last in cells:
            # A meeting across two months reads "Apr/May" and ends in the second.
            month = MONTHS.get(months.split("/")[-1][:3].lower())
            if month is None:
                raise SourceError("The Federal Reserve page changed format")
            day = date(year, month, int(last or first))
            if day >= today:
                events.append(Event(f"fomc:{day}", "fomc", "FOMC decision", "economic", HIGH, day, _at(day, FOMC_TIME)))
    if not years[1:]:
        raise SourceError("The Federal Reserve page changed format")
    return events


def parse_earnings(payload: dict, today: date) -> list[Event]:
    events = []
    for row in payload.get("earningsCalendar", []):
        day = date.fromisoformat(row["date"])
        symbol = row["symbol"]
        if day >= today:
            events.append(
                Event(
                    f"finnhub:{symbol}:{day}",
                    "finnhub",
                    f"{symbol} earnings",
                    "earnings",
                    MEDIUM,
                    day,
                    timing=TIMINGS.get(row.get("hour") or ""),
                )
            )
    return events


async def _get(client: httpx.AsyncClient, label: str, url: str, params: dict) -> httpx.Response:
    # Report the failure's type and status only: the URL carries the API key.
    try:
        response = await client.get(url, params=params)
    except httpx.HTTPError as e:
        raise SourceError(f"{label} couldn't be reached ({type(e).__name__})") from None
    if response.status_code != 200:
        raise SourceError(f"{label} returned HTTP {response.status_code}")
    return response


async def fetch_fred(client: httpx.AsyncClient, key: str, today: date) -> list[Event]:
    events = []
    for release_id in RELEASES:
        params = {
            "api_key": key,
            "file_type": "json",
            "release_id": release_id,
            "realtime_start": today.isoformat(),
            "realtime_end": "9999-12-31",
            "include_release_dates_with_no_data": "true",
            "sort_order": "asc",
            "limit": 12,
        }
        response = await _get(client, "FRED", FRED_URL, params)
        events += parse_fred(release_id, response.json(), today)
    return events


async def fetch_fomc(client: httpx.AsyncClient, today: date) -> list[Event]:
    response = await _get(client, "The Federal Reserve site", FOMC_URL, {})
    events = parse_fomc(response.text, today)
    if not events:
        raise SourceError("The Federal Reserve page changed format")
    return events


async def fetch_earnings(client: httpx.AsyncClient, key: str, symbols: list[str], today: date) -> tuple[list[Event], list[str]]:
    # One request per symbol: an unfiltered call stops at 1,500 rows and can miss near dates.
    events: list[Event] = []
    refused: list[str] = []
    for symbol in symbols:
        params = {"from": today.isoformat(), "to": (today + timedelta(days=FETCH_DAYS)).isoformat(), "symbol": symbol, "token": key}
        try:
            response = await client.get(FINNHUB_URL, params=params)
        except httpx.HTTPError as e:
            raise SourceError(f"Finnhub couldn't be reached ({type(e).__name__})") from None
        # The free plan refuses most foreign listings; that mustn't cost the other symbols.
        if response.status_code in (403, 404):
            refused.append(symbol)
        elif response.status_code != 200:
            raise SourceError(f"Finnhub returned HTTP {response.status_code}")
        else:
            events += parse_earnings(response.json(), today)
    if symbols and len(refused) == len(symbols):
        raise SourceError("Finnhub refused every symbol in the watchlist")
    return events, refused
