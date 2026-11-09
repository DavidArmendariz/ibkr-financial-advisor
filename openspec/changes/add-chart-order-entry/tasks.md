# Tasks

## 1. Order building (no IBKR calls)

- [x] 1.1 Add `backend/trading/sessions.py`, mapping a time and the contract's hours to pre-market, regular, after-hours, overnight, or closed (overnight 20:00–3:50 ET, Sunday to Thursday); test each boundary, a half day, and the weekend
- [x] 1.2 Add order building for long and short: the 4:00–20:00 bracket (LMT parent, STP LMT and LMT children with outside-RTH and GTC) and the overnight set (OVERNIGHT LMT entry, then exits after the fill); test sides, prices, gap cap rounding, and that a plain STP is never built
- [x] 1.3 Add validation (stop and target on the correct sides, a value cap, live off, whole shares) and `TRADING_` settings; test each refusal

## 2. Trading session and safeguards

- [x] 2.1 Add `backend/trading/session.py`: a separate order-capable session on client ID +20 that matches the main connection's port and account, or refuses; test the mismatch and a disconnect
- [x] 2.2 Add `backend/trading/broker.py` as the only module that sends orders: a review builds the orders, runs IBKR's what-if check, and returns a single-use token bound to the orders, mode, and account, expiring in 2 minutes; `send`, `modify`, and `cancel` require a valid token; test expiry, reuse, a changed account, live off, and the cap
- [x] 2.3 Replace `tests/test_orders.py`'s backend-wide ban with "order calls only in `trading/broker.py`", and keep the main connection's `readonly=True` with a test

## 3. Brackets and the overnight stop

- [x] 3.1 Add `TradeBracket` and `WatchedStop` tables, and track order status and fills from the trading session by perm ID; test a fill, a rejected exit after a fill (unprotected warning and notification), and a cancel
- [x] 3.2 Add the overnight flow: after the entry fills, place the SMART stop-limit and take profit pair, plus the OVERNIGHT take profit in one OCA group, and register the watched stop; test the order of calls
- [x] 3.3 Add `backend/trading/watcher.py`: watch the bid or ask, and on a cross cancel the take profit, send the capped exit limit, and notify, then notify again after 60 seconds unfilled; resume after a restart and record watching gaps; test long and short crosses, no cross on a stale last trade, the 60-second alert, and resumption
- [x] 3.4 Add the endpoints `POST /api/trading/review`, `POST /api/trading/confirm`, `POST /api/trading/brackets/{id}/review-modify` and `review-cancel`, and `GET /api/trading/state`; test each, including that nothing is sent without a valid token

## 4. View

- [x] 4.1 Add `OrderChart` with candles including extended hours, live bid and ask, and draggable entry, stop, and target lines that write back to the planner; check dragging snaps to cents and blocks a stop on the wrong side
- [x] 4.2 Add the long or short switch, the review panel (PAPER or LIVE, account, each order and its session, risk and reward, commission and margin from what-if, and the overnight warning), and Confirm, with a distinct live confirmation
- [x] 4.3 Show working brackets on the chart, with drag-to-modify and cancel through a review, and the app-watched stop's status and any watching gaps
- [x] 4.4 Add the Trading settings (live switch, value cap, gap cap) with an explanation of live TWS's Read-Only API

## 5. Paper verification during live sessions

- [ ] 5.1 After-hours on paper: place a 1-share SOXL bracket with the stop-limit near the price, and confirm it triggers and the take profit is cancelled
- [x] 5.2 Overnight on paper: confirm SOXL and SOXS bid and ask stream on OVERNIGHT, the OCA group cancels across SMART and OVERNIGHT, and the watched stop fires with the capped limit; if bid and ask don't stream, refuse overnight brackets with a message
- [ ] 5.3 On paper, short 1 share of SOXS in after-hours and overnight, and record what IBKR allows

## 6. Docs and verification

- [x] 6.1 Update the README (order entry, sessions, the overnight stop's limits, the live switch, answering No to TWS's precaution bypass) and `CLAUDE.md` (the rule change, the trading module, the IBKR order findings)
- [x] 6.2 Verify `uv run pytest`, `npx tsc --noEmit -p .`, and `npx vite build` pass
- [x] 6.3 Look at the chart, review, and working-bracket views in a browser with order endpoints mocked, at full and narrow widths, then place and cancel one paper bracket from the app

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
- Use it on live only after tasks 5.1–5.3 pass and live trading is switched on.
