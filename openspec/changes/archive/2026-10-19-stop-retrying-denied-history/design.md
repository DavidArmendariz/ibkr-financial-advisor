# Design

## Context

`MacroService._tick_slot` refreshes each slot's bars every `BARS_INTERVAL` (5 min) by calling `_refresh_bars`, which makes two `reqHistoricalData` requests (5-minute bars for the session, daily bars for 5 days). IBKR reports refusals asynchronously through `errorEvent`. `_on_error` matches the error to a slot by `conId` and stores code 162/165/366 as `slot.bars_error`, which the card shows only when it has no other value. `_on_disconnected` runs on a disconnect, on error 1101, and when the user switches ports, because `ibkr_service._connect` disconnects first.

Error 162 is IBKR's catch-all "Historical Market Data Service error". Its message tells the cases apart: "No market data permissions for …" is a missing subscription, while "HMDS query returned no data" or "pacing violation" are temporary.

## Goals / Non-Goals

**Goals:**
- No historical requests for an indicator after IBKR refuses it for lack of permission, until the next connection.

**Non-Goals:**
- Changing how streaming refusals (`DATA_ERROR_CODES`) retry. They already back off for 5 minutes and cost a single line.
- Hiding the Dow Jones card or making IBKR permissions configurable.

## Decisions

**Match on the message text, not only the code.** Mark a slot as denied when the code is 162 and the message contains "No market data permissions". Alternative: treat every 162 as permanent. That would also stop retrying after a pacing violation or an empty answer, which go away on their own.

**Reset on reconnect, not on a timer.** A `bars_denied` flag on the slot is cleared in `_on_disconnected`, so the first tick after a connection requests bars again. Alternative: back off to a longer interval (an hour, say). That still logs the error repeatedly, and a permission only changes when the user buys a subscription or switches accounts, and both of those come with a reconnect: TWS has to re-log for new permissions, and a paper/live switch disconnects first.

**Skip only the bars, keep the stream.** `_tick_slot` still resolves the contract and keeps the `reqMktData` subscription. Only `_refresh_bars` is skipped. It also stops after its first request when that one is denied, since the error arrives before the request returns; otherwise the daily request would be refused once more. The delayed stream is requested separately from the history and may still be allowed when the history is refused, so the card can still show a value. If the stream is refused too, it already backs off through `DATA_ERROR_CODES`.

IBKR dependency: this hinges on the account's historical-data permission for the index's exchange (CME IND for INDU). There's no pacing or market-hours dependency beyond making fewer requests.

## Risks / Trade-offs

- [IBKR rewords the message] → The flag simply never gets set, and the service falls back to today's 5-minute retry. Nothing breaks.
- [The user buys the subscription without restarting TWS] → IBKR applies new permissions only after a re-login anyway, which drops the API connection and clears the flag.
