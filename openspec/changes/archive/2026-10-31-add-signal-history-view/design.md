# Design

## Context

See proposal.md for motivation and specs/ for required behavior.

`SignalEvent` stores every signal in SQLite with an indexed `time`, a `signal_type` column, and a JSON `payload` holding the indicators, 20 bars, LLM decision, notified flag, and category. `SignalService.history` keeps only the latest 50 in memory, and `SignalTable` renders them. The database has no signals yet, so all of this is tested with seeded rows.

## Goals / Non-Goals

**Goals:**

- Browse every saved signal, with a filter by trigger, and keep the list current.

**Non-Goals:**

- Date range search, export, charts, or outcome statistics for signals.
- Deleting signals or a retention limit. About 34 alerts per session is roughly 8,500 rows a year, which SQLite handles easily.
- Changing the Signals view, or where notification clicks lead.

## Decisions

### Page with a cursor of time and id

`GET /api/signals/history?limit=100&type=EMA_CROSS&before=<cursor>` orders by `time` then `id`, both descending, and returns `{signals, next_cursor}`. The cursor holds the last row's time and id. It fetches one extra row to know whether more remain.

- *Alternative: `offset`.* Lost because new signals shift every row, so paging would repeat rows.
- *Alternative: a cursor of time alone.* Lost because triggers on one bar share a time, so a page boundary could skip or repeat them.

### Filter on `signal_type`

The filter uses the existing column, and a request with an unknown type gets a 422.

- *Alternative: filter by category.* Lost because category lives in the JSON payload, and the user wants to judge individual triggers.

### Read the database, not the in-memory history

A new `SignalService.history_page()` queries `SignalEvent`, sharing row-to-record code with `_load_history`.

- *Alternative: enlarge the in-memory list.* Lost because the list would still have a limit, and memory would grow with history.

### Leave `bars` out of the list response

Each row's 20 bars aren't shown, and would add about 100 rows × 20 bars to every poll. `SignalTable` accepts records without them.

- *Alternative: return full records.* Lost because of the wasted payload.

### Poll the first page and merge by id

`useSignalHistory`, mounted only by the page, refetches the newest page every 15 seconds and merges new rows at the top by `id`, so older pages stay loaded. Changing the filter resets the list.

- *Alternative: use the Signals WebSocket.* Lost because it streams live bars the view doesn't need, and a filtered merge isn't simpler. Polling also matches `usePortfolio`.

### A separate sidebar item below Signals

The tab is `signal-history` in `AppTab`, with the `History` icon, as the user asked.

- *Alternative: a tab inside the Signals view.* Lost because the user asked for a sidebar item.

## IBKR dependencies

None. The view makes no IBKR requests, needs no market data permissions, and isn't affected by pacing or market hours. The app's connection guard still applies, so the view is only reachable once connected, but a later drop doesn't stop it reading local data.

## Risks / Trade-offs

- [Stored times have no time zone] → `_load_history` already treats them as UTC. The cursor compares against stored values in the same form, and a test covers it.
- [A burst of more than 100 new signals between polls] → Not realistic with cooldowns, which allow about 3 triggers every few minutes.
- [Rows from before categories existed have no category] → The table already handles a missing category.
