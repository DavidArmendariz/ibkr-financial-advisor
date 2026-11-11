from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

import httpx

TIMEOUT = 20.0
BASE_URL = "https://api.stlouisfed.org/fred"
SERIES_ID = "M2SL"
# H.6 Money Stock Measures, the Fed release M2SL comes from.
RELEASE_ID = 21


class SourceError(Exception):
    pass


@dataclass(frozen=True)
class Fetched:
    observations: list[tuple[str, float]]  # (YYYY-MM-01, billions), oldest first
    last_updated: Optional[datetime]
    next_release: Optional[date]


def parse_observations(payload: dict) -> list[tuple[str, float]]:
    rows = []
    for obs in payload["observations"]:
        # FRED writes a missing value as "."
        if obs["value"] == ".":
            continue
        rows.append((obs["date"], float(obs["value"])))
    rows.sort()
    return rows


def parse_last_updated(payload: dict) -> Optional[datetime]:
    raw = payload["seriess"][0].get("last_updated")
    if not raw:
        return None
    # FRED sends "2026-10-27 12:01:34-05": an hour-only offset that %z won't take.
    if len(raw) >= 3 and raw[-3] in "+-" and raw[-4].isdigit():
        raw += "00"
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S%z").astimezone(timezone.utc)
    except ValueError:
        return None


def parse_next_release(payload: dict, today: date) -> Optional[date]:
    days = sorted(date.fromisoformat(d["date"]) for d in payload.get("release_dates", []))
    return next((d for d in days if d >= today), None)


async def _get(client: httpx.AsyncClient, path: str, params: dict) -> httpx.Response:
    # Report the failure's type and status only: the URL carries the API key.
    try:
        response = await client.get(f"{BASE_URL}/{path}", params=params)
    except httpx.HTTPError as e:
        raise SourceError(f"FRED couldn't be reached ({type(e).__name__})") from None
    if response.status_code != 200:
        raise SourceError(f"FRED returned HTTP {response.status_code}")
    return response


async def fetch_m2(client: httpx.AsyncClient, key: str, today: date) -> Fetched:
    common = {"api_key": key, "file_type": "json"}
    try:
        observations = parse_observations((await _get(client, "series/observations", {**common, "series_id": SERIES_ID})).json())
        last_updated = parse_last_updated((await _get(client, "series", {**common, "series_id": SERIES_ID})).json())
    except (ValueError, KeyError, TypeError, IndexError):
        raise SourceError("FRED sent an unexpected reply") from None
    if not observations:
        raise SourceError("FRED sent no M2 data")
    next_release = None
    try:
        params = {
            **common,
            "release_id": RELEASE_ID,
            "realtime_start": today.isoformat(),
            "realtime_end": "9999-12-31",
            "include_release_dates_with_no_data": "true",
            "sort_order": "asc",
            "limit": 5,
        }
        next_release = parse_next_release((await _get(client, "release/dates", params)).json(), today)
    except (SourceError, ValueError, KeyError, TypeError):
        pass  # best-effort: the view just leaves the date out
    return Fetched(observations, last_updated, next_release)
