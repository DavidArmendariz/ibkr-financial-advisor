# Design

## Context

`MacroService` streams with `reqMktData` and adds 5-minute and daily bars per indicator, with `parse_trading_hours`, `is_open`, and a `Sparkline` component available to reuse. A live probe on Nov 1, 2026 (19:40 ET, with Seoul and Tokyo open, Europe closed) on the paper account found:

| Instrument | Contract that works | Latest 5-minute bar at 09:40 Seoul/Tokyo |
| --- | --- | --- |
| KOSPI 200 | `Index K200 KSE KRW` | 09:15 |
| Nikkei 225 | `Index N225 OSE.JPN JPY` | 09:15 |
| AEX | `Index EOE FTA EUR` | daily bars confirmed; closed |
| Euro Stoxx 50 | `Index ESTX50 EUREX EUR` | daily bars confirmed; closed |
| Samsung, SK Hynix | `Stock 005930 / 000660 SMART KRW` | 09:40 |
| TSMC | `Stock 2330 TWSE TWD` | Friday; Taiwan had not opened |
| Tokyo Electron, Advantest, Disco, Renesas | `Stock 8035 / 6857 / 6146 / 6723 SMART JPY` | 09:15 |
| ASML, ASM International, BESI | `Stock ASML / ASM / BESI AEB EUR` | closed |
| Infineon, STMicroelectronics | `Stock IFX / STMPA SMART EUR` | closed |

Named direct exchanges `IBIS`, `SBF`, and `TSEJ` refused bars with error 162, while `SMART` worked. `AEB` works when named. `SMART` leaves out Amsterdam's closing auction: ASML's Oct 30 close was 1409.9 on `SMART` and 1412.8 on `AEB`. In Tokyo, `SMART` adds off-exchange trades from 17:00. `reqMktData` with type 4 returned nothing and no error, even with Tokyo open. A KOSPI composite contract wasn't found: symbol search lists `K200`, `K200M`, and `K300`.

## Goals / Non-Goals

**Goals:**

- One view of how Asia, Europe, and their chip stocks moved.
- Honest timing, since data lags by a different amount per market.

**Non-Goals:**

- Live quotes.
- A user-editable instrument list, or settings of any kind.
- Converting to USD, or comparing ASML in Amsterdam with its US listing.
- Alerts, or feeding this data to signals or the AI Advisor.
- Other Asian or European indexes, such as TOPIX.

## Decisions

### Use bars only

Each instrument refreshes from historical bars.

- *Alternative: stream with `reqMktData`, as Macro does.* Lost because the probe got no data from it, and it would use up market data lines.

### Add a separate service and view

A new `backend/global_markets/` holds the instrument list and service, reusing helpers from `backend/macro/indicators.py`.

- *Alternative: add these as Macro indicators.* Lost because Macro's slots are built around streaming tickers, and its spec lists exactly 11 indicators.
- *Alternative: a section inside the Macro page.* Lost because the user asked for a sidebar item.

### Show the KOSPI 200

- *Alternative: the KOSPI composite.* Lost because IBKR's symbol search shows no such index. The card says KOSPI 200, because the two aren't the same number.

### Show the AEX and the Euro Stoxx 50

The AEX is ASML's home index, and ASML is a large share of it. The Euro Stoxx 50 adds a wider European reading, which the user didn't name, but they weren't sure which index they wanted.

- *Alternative: only one.* Lost because the AEX alone is mostly a few large stocks, and the Euro Stoxx 50 alone dilutes chips.

### Show each company's home listing

- *Alternative: US-listed ADRs and ETFs such as TSM or EWY.* Lost because they only trade during US hours, which defeats the overnight purpose.

### Use `SMART` for stocks, with the primary exchange set, except in Amsterdam

The primary exchange and currency keep each contract on the home listing. Amsterdam names `AEB` directly, so its closes include the auction. TSMC names `TWSE`, the form the probe confirmed.

- *Alternative: name the direct exchange everywhere.* Lost because the probe got error 162 for Frankfurt, Paris, and Tokyo.
- *Alternative: `SMART` everywhere.* Lost because ASML's close would be wrong.

### Keep only the latest regular session in the sparkline

Bars are requested over 2 days, cut to the last local date, and Tokyo stocks also drop bars from 15:30, because `SMART` adds evening off-exchange trades.

- *Alternative: rely on the request's regular-hours flag.* Lost because the probe's Tokyo bars ran from 17:00 Friday to Monday with it set.

### Use daily bars for the previous close

Daily bars refresh when a session changes, and 5-minute bars refresh while open.

- *Alternative: take the close from 5-minute bars.* Lost because daily bars are the exchange's own session record, and Tokyo's `SMART` 5-minute bars run past the close.

### Hours come from each contract

`reqContractDetails` gives each contract's `liquidHours` and time zone, parsed with `parse_trading_hours`. Lunch breaks in Tokyo count as closed.

- *Alternative: fixed hours per market.* Lost because of holidays and half-days.

## IBKR dependencies

Historical TRADES bars and contract details, on the shared connection, working on the paper account. At most 16 5-minute requests per 5 minutes, and usually far fewer because the regions barely overlap. Requests run one at a time so a pass isn't a burst, and bars of this size aren't subject to the small-bar pacing limit. Delays differ per market and aren't guaranteed, so the card shows the bar's time and doesn't claim a fixed delay. Live-account permissions could differ from paper, in which case that card shows IBKR's error.

## Risks / Trade-offs

- [Frankfurt and Paris can't be named directly, so `SMART` may miss their closing auctions as it does Amsterdam's] → Infineon and STMicro closes can differ slightly from the official ones, and both are shown as IBKR reports them.

- [Taiwan and Europe's intraday bars weren't seen during their open hours] → Task 4.4 checks them while those markets are open, and the design changes if they don't flow.
- [Indexes lagged about 25 minutes in the probe] → Shown on the card. This suits an overnight read, not timing.
- [Symbols or contracts change] → That card shows the error, and others are unaffected.
- [Won't update while the app is closed] → Accepted. The next launch fills the data in.
