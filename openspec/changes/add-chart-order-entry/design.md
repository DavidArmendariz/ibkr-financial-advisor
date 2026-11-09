# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

- **The shared connection:** `ibkr_service` connects with `readonly=True`. Without it, ib_async requests open and completed orders on every connect, which TWS refuses with a pop-up when Read-Only API is on, as live had it on Nov 1. `tests/test_orders.py` fails if `placeOrder`, `cancelOrder`, `reqGlobalCancel`, or `reqAutoOpenOrders` appears anywhere in `backend/`.
- **Paper test on Nov 8, 2026 (SOXL, account DUT147902):**
  - **SMART:** a LMT with outside-RTH was Submitted. A STP was PreSubmitted, with warning 2109 ("Outside Regular Trading Hours is ignored"). A STP LMT was PreSubmitted with no warning.
  - **OVERNIGHT:** the what-if check accepted a LMT. STP and STP LMT got error 387, "Unsupported order type".
  - **TWS precautions:** a directed OVERNIGHT order gets 10329 ("directly routed to OVERNIGHT", a TWS precaution), and TWS asked whether to bypass precautions for API orders. The user should keep them.
  - **Clean-up:** all test orders were cancelled.
- **Existing pieces to reuse:**
  - The Trade Planner already has SOXL and SOXS ATR, live bid and ask (`reqMktData` on qualified contracts), account net liquidation and available funds, and the sizing math in `planner/calc.py`.
  - The Signals chart uses lightweight-charts 4.2 with price lines and series primitives.
  - Native notifications come from the signals WebSocket through Electron.

## Goals / Non-Goals

**Goals:**

- Place an entry with a stop and target in one confirmation, with the right order types for the session.
- Make it hard to send an order by accident, and make an app-watched stop's limits obvious.

**Non-Goals:**

- Symbols other than SOXL and SOXS.
- Attaching exits to shares bought outside the app, or managing orders placed in TWS.
- Market orders, trailing stops, or algorithms.
- Cancelling or editing orders from the Orders view, which stays read-only.
- Automatic trading from signals.

## Decisions

### A separate trading session; the main connection stays read-only

`backend/trading/session.py` opens a second `IB()` on the same host and port as the main connection, with client ID `IBKR_CLIENT_ID + 20` and `readonly=False`. It opens when an order is sent, modified, or cancelled, and stays open while any app-watched stop is active. It refuses to open if the main connection's port and managed account don't match.

- *Alternative: drop `readonly` on the main connection.* Lost because every feature would then run on an order-capable session, and connects would request completed orders, which live TWS refuses while its Read-Only API is on.

### One module sends orders, and only with a confirmation token

All `placeOrder` and `cancelOrder` calls live in `backend/trading/broker.py`. The test changes from "nowhere in `backend/`" to "only in `broker.py`".

A review returns a token bound to:

- the exact order list,
- the mode and account,
- and an expiry 2 minutes later.

`broker.send(token)` re-checks the mode, the account, live trading being on, and the value cap before sending. Tokens are single-use.

- *Alternative: a confirm flag in the request.* Lost because it can't prove that what's sent is what was reviewed.

### Session-aware order structures

Session boundaries come from the contract's `liquidHours` and `tradingHours`, with 4:00, 9:30, 16:00, and 20:00 ET as fallbacks. The overnight window is 20:00–3:50 ET, Sunday to Thursday nights.

- **4:00–20:00:**
  - **Parent:** a LMT entry on SMART, with `outsideRth=True`, `tif=GTC`, and `transmit=False`.
  - **Children:** a STP LMT stop (limit = trigger ∓ gap cap) and a LMT take profit, both with `outsideRth` and GTC.
  - **Linking:** `parentId` plus the last child transmitting, so IBKR treats it as one bracket.
- **20:00–3:50:**
  - The entry LMT goes on the OVERNIGHT venue as a DAY order.
  - Once it fills, the app places a GTC SMART STP LMT and LMT exit pair, both outside-RTH, in a fresh OCA group. They don't trade overnight, but they're ready for 4:00.
  - The app also adds an OVERNIGHT LMT take profit in the same OCA group, and an app-watched stop.
  - OVERNIGHT orders expire at the end of the session, which is the hand-off.
- **Plain STP isn't used** in any session, because outside-RTH is ignored on it.

- *Alternative: the user's two-limit idea.* Lost because the lower limit fills at once.
- *Alternative: a STP bracket in regular hours, swapped for STP LMT at 16:00.* Lost because one structure for 4:00–20:00 means no swaps, and nothing changes while a session hands over.

### App-watched stop

`backend/trading/watcher.py` loads active watched stops from SQLite (`WatchedStop`: bracket, side, level, gap cap, state) and subscribes to bid and ask through the trading session. When a long position's bid is at or below its stop (a short's ask at or above), it:

1. cancels the overnight take profit, then
2. sends an exit LMT at the bid × (1 − cap), or the ask × (1 + cap), on OVERNIGHT, then
3. notifies, and notifies again if the exit isn't filled in 60 seconds.

The stop is crossed on the best bid or ask, not the last trade, because overnight prints are sparse and can be stale, as seen with exchange "D" prints. Gaps in watching (app down, disconnected) are recorded and shown.

- *Alternative: crossing on the last trade.* Lost because the last trade can lag the book by minutes overnight.
- *Alternative: only alert.* Lost because the user chose to exit automatically with a price cap.

### Brackets are persisted

The `TradeBracket` table stores the order IDs, perm IDs, levels, mode, account, and state. Fills and status come from the trading session's `orderStatusEvent` and execution events, matched by perm ID. The existing fills capture still records fills for the Orders view.

### Chart and dragging

A new `OrderChart` uses lightweight-charts candles from 1-minute bars with `useRTH=False`, plus the planner's live bid and ask. It draws three price lines, and dragging is done with pointer events and `series.coordinateToPrice`, snapping to $0.01. The lines start from the planner's ATR values, and dragging writes back to the planner's inputs. Working orders draw solid lines, and a draft draws dashed ones.

- *Alternative: another chart library with built-in dragging.* Lost because it adds a dependency, and lightweight-charts is already used and handles this with a primitive.

### Safeguards in Settings

The `TRADING_` prefix holds:

- `live_enabled`, default false,
- `max_order_value`, default $25,000, used for paper and live,
- `gap_cap_percent`, default 1.

The live review uses a red banner naming the account, and a "Place LIVE order" button. TWS's own precautions stay on, and the README tells the user to answer No to the bypass prompt.

## IBKR dependencies

- **Live Read-Only API:** live trading needs it turned off in live TWS. Paper already has it off.
- **Pacing:** order rate is a few orders per bracket. Plus one bid/ask subscription per watched stop in the trading session, inside the ~100 line limit.
- **Overnight data:** overnight prices need the bid and ask to stream on the OVERNIGHT venue, which isn't verified yet (task 5.2). Without it, overnight brackets are refused, with a message.
- **Short selling:** shorting SOXS needs shares available to borrow, and IBKR's rejection message is shown if not.

## Risks / Trade-offs

- [The app-watched stop fails while the Mac sleeps, the backend restarts, or TWS disconnects] → Warned before confirming, gaps shown afterwards, and the 4:00 bracket is already resting at IBKR.
- [A stop-limit doesn't fill on a gap past its limit] → The limit sits a gap-cap past the trigger, and the review explains it.
- [A wrong order on live] → Live off by default, a value cap, a distinct review, single-use tokens bound to the review, and TWS precautions kept.
- [Not yet verified: OCA across SMART and OVERNIGHT, stop-limit triggering after-hours, and overnight shorting] → Tested on paper during live sessions (tasks 5.1–5.3) before live use. If OCA doesn't span venues, the watcher cancels the other side on a fill.
- [Removing a long-standing guard] → Narrowed to one module and a token check, with tests that fail if order calls appear elsewhere.
