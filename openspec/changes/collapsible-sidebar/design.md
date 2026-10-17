# Design

## Context

`Layout.tsx` renders a fixed `w-56` `Sidebar` next to `<main className="flex-1">`. The sidebar's 48 px header is the window's drag region and, on macOS (`titleBarStyle: 'hiddenInset'`), is padded with `pl-20` so the traffic-light buttons don't cover the logo. The page components have no header bar of their own: they start with `p-6` content. The connection indicator lives in the sidebar footer, and the ibkr-connection spec requires it to be visible at all times.

All chart components already follow their container's width: `TradingChart`, `SignalChart` and `GammaByStrikeChart` with a `ResizeObserver`, `ChartBlock` with Recharts' `ResponsiveContainer`.

The renderer already keeps one per-device preference in `localStorage` (the AI Advisor risk profile in `pages/Chat.tsx`).

## Goals / Non-Goals

**Goals:**
- Hide the sidebar completely and restore it, from the mouse or the keyboard, with the choice surviving restarts.
- Keep the macOS window draggable, the traffic lights clear, and the connection status visible in both states.

**Non-Goals:**
- An icon-only rail or a resizable sidebar width.
- Hiding the AI Advisor's own conversation list.
- Hiding the sidebar automatically on narrow windows.

## Decisions

**Top bar while hidden, not a floating button.** When hidden, `Layout` renders a 48 px bar above `<main>` (same height as the sidebar header): `drag-region`, `pl-20` on macOS, a "show sidebar" button on the left and the connection indicator on the right. Alternative: a small floating button over the top-left corner of the page. It costs no vertical space, but it would sit on top of the page titles (pages start at 24 px), the window would have no drag region, the traffic lights would cover it on macOS, and the connection status would disappear, against the ibkr-connection spec. The bar costs 48 px of height to gain 224 px of width, which is the dimension the user is short of.

**Shared `ConnectionIndicator` component.** The dot + "Connected · Paper" markup moves out of `Sidebar` into its own component, used by the sidebar footer and the top bar. Alternative: duplicate the markup in the bar; two copies would drift (colour, wording).

**State lives in `Layout`, persisted by a small hook.** `useSidebarCollapsed()` reads and writes a `localStorage` key (`deltaadvisor.sidebarCollapsed`), wrapped in try/catch so a blocked storage just falls back to "shown". Alternative: persist it to `.env` through the backend like other settings. That convention is for backend-applied settings; this is a per-window UI preference, and a round trip would make the sidebar flash open on launch before the value arrives. `localStorage` is synchronous, so the first render is already correct. In Electron it lives in the app's userData, so it survives restarts and updates.

**Keyboard shortcut handled in the renderer.** A `keydown` listener on `window` in `Layout` toggles on Cmd+B (macOS, `isMac`) or Ctrl+B, and calls `preventDefault()`. Alternative: an Electron menu accelerator. It wouldn't work in the browser version, which the user runs day to day, and would need IPC to reach the renderer. The listener ignores events with Shift/Alt held, so Ctrl+Shift+B (browser bookmarks bar) passes through.

**No width animation.** The sidebar is removed from the layout instantly. Alternative: a ~200 ms width transition. During it every chart's `ResizeObserver` fires on each frame, and lightweight-charts redraws each time; an instant switch resizes once. It can be added later if it feels abrupt.

**Unmount rather than hide with CSS.** The hidden sidebar is not rendered. It holds no state of its own (the active tab and the portfolio summary live in `Layout`/`App`), so nothing is lost, and a `display: none` element would still be reachable by tab focus in some browsers.

No IBKR data, permissions, pacing or market-hours dependency: this is layout only. `usePortfolio` keeps polling in `Layout` whether the sidebar is shown or not, so the Dashboard is unaffected.

## Risks / Trade-offs

- [Cmd+B / Ctrl+B is "bold" in rich-text editors] → The app has no rich-text fields; the AI Advisor box is a plain textarea where the combination does nothing. Spec'd so it toggles even there.
- [Firefox uses Ctrl+B for its bookmarks sidebar] → `preventDefault()` takes priority for page-focused key events; Chrome and Electron don't bind it.
- [The bar takes 48 px of height, so page content moves down when the sidebar hides] → Accepted (see the first decision).
