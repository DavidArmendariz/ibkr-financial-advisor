# Tasks

## 1. Shared pieces

- [x] 1.1 Move the connection dot + label from `Sidebar.tsx` into `src/components/ConnectionIndicator.tsx` and use it in the sidebar footer; verify `npx tsc --noEmit -p .` passes and the footer still reads "Connected · Paper" in the browser
- [x] 1.2 Add `src/hooks/useSidebarCollapsed.ts` (state + `localStorage` key `deltaadvisor.sidebarCollapsed`, try/catch on read and write, default shown); verify with tsc

## 2. Hide and restore

- [x] 2.1 Add a hide button (`PanelLeftClose`, `no-drag`, aria-label and title showing the shortcut) to the right of the sidebar header; verify it hides the sidebar and the view fills the window
- [x] 2.2 In `Layout.tsx`, when collapsed skip the `Sidebar` and render the 48 px top bar above `<main>`: `drag-region`, `pl-20` when `isMac`, show button (`PanelLeftOpen`, `no-drag`) on the left, `ConnectionIndicator` on the right; verify the show button restores the sidebar with the same tab selected
- [x] 2.3 Add the Cmd+B (macOS) / Ctrl+B `keydown` listener in `Layout` with `preventDefault()`, ignoring Shift/Alt combinations; verify it toggles both ways, including while focused in the AI Advisor message box, without inserting text
- [x] 2.4 Update the README feature line about the sidebar footer to mention hiding the sidebar and the shortcut; verify the text matches the behavior

## 3. Verification

- [x] 3.1 Run `uv run pytest`, `npx tsc --noEmit -p .` and `npx vite build`; all pass
- [x] 3.2 In the browser at http://localhost:5273: hide and show the sidebar on Dashboard, AI Advisor, Signals, Gamma and Settings; check that charts resize to the new width, the top bar shows the connection status, and a reload keeps the hidden state
- [x] 3.3 Check the macOS app (or note it as not checked when only WSL is available): the top bar clears the traffic lights and drags the window
  - Checked by the user on macOS.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, so `app-navigation` becomes a main spec and the ibkr-connection scenario is merged.
