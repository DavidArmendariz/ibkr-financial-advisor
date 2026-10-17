# Proposal

## Why

The sidebar always takes 224 px, which the Dashboard chart, the Signals chart and the Gamma view could use. On a laptop screen, or with the window split next to TWS, the main view gets cramped. The user wants to hide the sidebar when they need the room.

## What Changes

- A control in the sidebar header hides the sidebar completely, and the main view takes the full window width.
- While the sidebar is hidden, a slim top bar spans the main view. It holds a control to show the sidebar again and the connection status, and on macOS it is where the window is dragged from and leaves room for the window buttons.
- Cmd+B on macOS (Ctrl+B elsewhere) toggles the sidebar.
- The app remembers whether the sidebar was hidden and restores that on the next launch.
- The connection status stays visible when the sidebar is hidden. The Net Liq. Value card goes with the sidebar; the Dashboard still shows it.

This change doesn't touch IBKR access, order handling, API keys, or send data off the machine. It only changes the renderer layout, and the hidden/shown preference stays in the renderer's local storage on this machine.

## Capabilities

### New Capabilities
- `app-navigation`: How the user moves between the app's views through the sidebar, including hiding and restoring it.

### Modified Capabilities
- `ibkr-connection`: "Connection status is visible" now also covers the hidden sidebar: the top bar shows the status there.

## Impact

- `src/components/Sidebar.tsx`: hide control in the header.
- `src/components/Layout.tsx`: hidden/shown state, top bar, keyboard shortcut.
- New hook for the persisted preference (`src/hooks/useSidebarCollapsed.ts`).
- README feature list (the sidebar footer line).
- No backend, API or dependency changes. The `lucide-react` icons used are already a dependency.
