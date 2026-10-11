import math
from datetime import date, datetime

import pytest

from backend.gamma.calc import (
    OptionRow,
    bs_gamma,
    by_expiry,
    by_strike,
    dollar_gamma,
    net_gex_at,
    summarize,
    years_to_expiry,
    zero_gamma_level,
)
from backend.signals.sessions import ET

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=ET)
EXP = date(2026, 10, 16)


def test_bs_gamma_hand_computed():
    # S=K=100, T=1, sigma=0.2, r=0: d1=0.1, gamma = phi(0.1) / (100*0.2) = 0.019848
    assert bs_gamma(100, 100, 1.0, 0.2) == pytest.approx(math.exp(-0.005) / math.sqrt(2 * math.pi) / 20, rel=1e-12)
    assert bs_gamma(100, 100, 1.0, 0.2) == pytest.approx(0.0198476, rel=1e-5)


def test_bs_gamma_matches_ibkr_model_greeks():
    # IBKR quoted SOXL 140C (Oct 16) at the Oct 9 close: und 139.73, IV 0.9558, gamma 0.02141.
    close = datetime(2026, 10, 9, 16, 0, tzinfo=ET)
    g = bs_gamma(139.73, 140, years_to_expiry(EXP, close), 0.9558)
    assert g == pytest.approx(0.02141, rel=0.03)


def test_dollar_gamma_scale_and_sign():
    call = OptionRow(EXP, 140, "C", open_interest=1000, gamma=0.02, iv=0.9)
    put = OptionRow(EXP, 140, "P", open_interest=1000, gamma=0.02, iv=0.9)
    # 0.02 * 1000 contracts * 100 shares * 140^2 * 1%
    assert dollar_gamma(call, 140) == pytest.approx(392_000)
    assert dollar_gamma(put, 140) == pytest.approx(-392_000)
    assert dollar_gamma(OptionRow(EXP, 140, "C", 0, 0.02, 0.9), 140) == 0
    assert dollar_gamma(OptionRow(EXP, 140, "C", 100, None, None), 140) == 0


def test_years_to_expiry_floors_at_one_hour():
    assert years_to_expiry(date(2026, 10, 9), datetime(2026, 10, 9, 17, 0, tzinfo=ET)) == pytest.approx(1 / (365 * 24))
    assert years_to_expiry(EXP, NOW) == pytest.approx((7 * 24 + 4) / (365 * 24))


def chain():
    return [
        OptionRow(EXP, 130, "P", 5000, 0.015, 1.0),
        OptionRow(EXP, 130, "C", 500, 0.015, 1.0),
        OptionRow(EXP, 140, "C", 3000, 0.021, 0.95),
        OptionRow(EXP, 140, "P", 2000, 0.021, 0.95),
        OptionRow(EXP, 150, "C", 6000, 0.019, 0.92),
        OptionRow(date(2026, 10, 23), 150, "C", 1000, 0.012, 0.9),
    ]


def test_aggregation_by_strike_and_expiry():
    rows = chain()
    strikes = {s.strike: s for s in by_strike(rows, 140)}
    assert strikes[150].call == pytest.approx(dollar_gamma(rows[4], 140) + dollar_gamma(rows[5], 140))
    assert strikes[150].call_oi == 7000
    assert strikes[130].put_oi == 5000 and strikes[130].put < 0
    expiries = by_expiry(rows, 140)
    assert [e["expiry"] for e in expiries] == [EXP, date(2026, 10, 23)]
    assert expiries[1]["net"] == pytest.approx(dollar_gamma(rows[5], 140))


def test_summary_walls_and_totals():
    s = summarize(chain(), 140, NOW)
    assert s["call_wall"] == 150
    assert s["put_wall"] == 130
    assert s["net_gex"] == pytest.approx(s["call_gex"] + s["put_gex"])
    assert s["contracts"] == 6
    assert s["expiries"][0]["expiry"] == "2026-10-16"


def test_zero_gamma_level_on_put_heavy_downside():
    # Puts below spot, calls above: exposure is negative low and positive high,
    # so the flip sits between the two strikes and net GEX changes sign across it.
    rows = [OptionRow(EXP, 120, "P", 10_000, 0.02, 0.6), OptionRow(EXP, 160, "C", 10_000, 0.02, 0.6)]
    flip = zero_gamma_level(rows, 140, NOW)
    assert flip is not None and 120 < flip < 160
    assert net_gex_at(rows, flip - 2, NOW) < 0 < net_gex_at(rows, flip + 2, NOW)


def test_zero_gamma_level_none_when_one_sided():
    rows = [OptionRow(EXP, 140, "C", 1000, 0.02, 0.9)]
    assert zero_gamma_level(rows, 140, NOW) is None
