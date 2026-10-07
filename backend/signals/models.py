from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Bar:
    time: datetime  # bar start, timezone-aware
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["time"] = self.time.isoformat()
        return d


@dataclass(frozen=True)
class IndicatorValues:
    vwap: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    bb_mid: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    rvol: Optional[float] = None

    def ready(self) -> bool:
        return None not in (self.vwap, self.ema_fast, self.ema_slow, self.bb_mid, self.rvol)

    def to_dict(self) -> dict:
        return asdict(self)
