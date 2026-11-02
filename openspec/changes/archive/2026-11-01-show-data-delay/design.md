# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

On Nov 2, 2026 at 11:22 Seoul, the KOSPI 200's latest bar was 11:00, while KODEX 200 (`069500`, KRX) and Samsung had 11:20. KODEX closed at 90,800 against the index's 897.30 on Oct 30, about 101 times. An audit found delayed data only in Macro and Asia & Europe. Signals uses the paid real-time feed, and Gamma is a timestamped snapshot.

## Goals / Non-Goals

**Goals:**

- A current read of the Korean index, never mistaken for the official one.
- A real figure wherever data is delayed.

**Non-Goals:**

- Estimates for other markets. Tokyo stocks lag with the Nikkei, so they already match.
- Delay labels on Signals, Gamma, or Dashboard.

## Decisions

### Estimate from percent change

The estimate is the index's previous close times one plus the ETF's percent change.

- *Alternative: a fixed ratio of about 101.* Lost because fees and dividends move the ratio over time.
- *Alternative: buy real-time Korean index data.* Lost because it costs money, and cards are built on bars anyway.

### Show it only while it adds something

The estimate shows only while Korea is open and the ETF's data is newer than the index's.

- *Alternative: always show it.* Lost because the official close is better once it exists.

### Measure the delay

Delay is now minus the latest bar's end. It includes the wait for the next refresh, which is what the user experiences.

- *Alternative: fixed labels such as "15 min delayed".* Lost because the real figure varies, and Samsung is near current.

The same measure applies to Macro, even when a delayed stream supplies the value, because its bars come from the same delayed feed.

### Fetch the ETF as a hidden instrument

It refreshes with the others, but gets no card or row of its own.

- *Alternative: a fifth card.* Lost because the user chose an estimate on the KOSPI card.

## IBKR dependencies

Works during Korean hours. Adds up to one 5-minute request per refresh and one daily request per session. Near-current KRX data was seen on paper, and the live account could differ.

## Risks / Trade-offs

- [The ETF can trade slightly above or below its holdings, mostly near the open] → Labelled as an estimate.
- [An ex-dividend day can make the ETF's percent change understate the index] → Accepted. It's rare, and the real index value is on the card.
- [The newest bar is still forming, so an estimate can shift] → Expected for a live estimate.
