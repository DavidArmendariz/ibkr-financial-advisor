from dataclasses import dataclass
from datetime import time
from typing import Callable, Optional

from ib_async import Contract, Index, Stock


ETF = "ETF"


@dataclass(frozen=True)
class Instrument:
    key: str
    label: str
    section: str
    group: str
    currency: str
    tz: str  # the market's own zone, for showing when the data is from
    place: str
    make_contract: Callable[[], Contract]
    decimals: int = 2
    # SMART adds evening off-exchange trades in Tokyo, which aren't the session.
    regular_end: Optional[time] = None


def _index(key: str, label: str, symbol: str, exchange: str, currency: str, tz: str, place: str) -> Instrument:
    return Instrument(key, label, "Indexes", "", currency, tz, place, lambda: Index(symbol, exchange, currency))


def _stock(
    key: str,
    label: str,
    group: str,
    symbol: str,
    currency: str,
    primary: str,
    tz: str,
    place: str,
    decimals: int = 2,
    exchange: str = "SMART",
    regular_end: Optional[time] = None,
) -> Instrument:
    # SMART gets bars where naming the exchange is refused (error 162); the primary
    # exchange and currency keep it on the home listing rather than an ADR.
    return Instrument(
        key, label, "Indexes" if group == ETF else "Chip stocks", group, currency, tz, place,
        lambda: Stock(symbol, exchange, currency, primaryExchange=primary), decimals, regular_end,
    )


SEOUL = ("Asia/Seoul", "Seoul")
TOKYO = ("Asia/Tokyo", "Tokyo")
TAIPEI = ("Asia/Taipei", "Taipei")
AMSTERDAM = ("Europe/Amsterdam", "Amsterdam")
FRANKFURT = ("Europe/Berlin", "Frankfurt")
PARIS = ("Europe/Paris", "Paris")
TOKYO_CLOSE = time(15, 30)

INSTRUMENTS: list[Instrument] = [
    _index("nikkei", "Nikkei 225", "N225", "OSE.JPN", "JPY", *TOKYO),
    # IBKR lists no KOSPI composite, and the two aren't the same number.
    _index("kospi200", "KOSPI 200", "K200", "KSE", "KRW", *SEOUL),
    # KRX stocks arrive near current while the index lags, so this ETF, which tracks
    # it, shows the market's move sooner.
    _stock("kodex200", "KODEX 200 ETF", ETF, "069500", "KRW", "KRX", *SEOUL, 0),
    _index("aex", "AEX", "EOE", "FTA", "EUR", *AMSTERDAM),
    _index("estx50", "Euro Stoxx 50", "ESTX50", "EUREX", "EUR", *FRANKFURT),
    _stock("samsung", "Samsung Electronics", "Korea", "005930", "KRW", "KRX", *SEOUL, 0),
    _stock("hynix", "SK Hynix", "Korea", "000660", "KRW", "KRX", *SEOUL, 0),
    _stock("tsmc", "TSMC", "Taiwan", "2330", "TWD", "TWSE", *TAIPEI, 0, exchange="TWSE"),
    _stock("tel", "Tokyo Electron", "Japan", "8035", "JPY", "TSEJ", *TOKYO, 0, regular_end=TOKYO_CLOSE),
    _stock("advantest", "Advantest", "Japan", "6857", "JPY", "TSEJ", *TOKYO, 0, regular_end=TOKYO_CLOSE),
    _stock("disco", "Disco", "Japan", "6146", "JPY", "TSEJ", *TOKYO, 0, regular_end=TOKYO_CLOSE),
    _stock("renesas", "Renesas", "Japan", "6723", "JPY", "TSEJ", *TOKYO, 0, regular_end=TOKYO_CLOSE),
    # Named directly: SMART misses Amsterdam's closing auction (1409.9 against 1412.8).
    _stock("asml", "ASML", "Netherlands", "ASML", "EUR", "AEB", *AMSTERDAM, exchange="AEB"),
    _stock("asm", "ASM International", "Netherlands", "ASM", "EUR", "AEB", *AMSTERDAM, exchange="AEB"),
    _stock("besi", "BE Semiconductor", "Netherlands", "BESI", "EUR", "AEB", *AMSTERDAM, exchange="AEB"),
    _stock("infineon", "Infineon", "Germany & France", "IFX", "EUR", "IBIS", *FRANKFURT),
    _stock("stm", "STMicroelectronics", "Germany & France", "STMPA", "EUR", "SBF", *PARIS),
]
