import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, compact = false): string {
  if (compact && Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPnL(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${formatCurrency(value)}`
}

export function pnlClass(value: number): string {
  if (value > 0) return 'text-emerald-400'
  if (value < 0) return 'text-red-400'
  return 'text-zinc-400'
}

declare global {
  interface Window {
    // Exposed by electron/preload.cjs; absent when the UI runs in a plain browser
    electronAPI?: {
      getAppVersion: () => Promise<string>
      openExternal: (url: string) => Promise<void>
      platform: NodeJS.Platform
      onNavigate?: (callback: (tab: string) => void) => () => void
    }
  }
}

// The window uses titleBarStyle "hiddenInset", so on macOS the traffic-light
// buttons are drawn over the top-left of the page and need room reserved.
export const isMac = window.electronAPI?.platform === 'darwin'

// isMac only covers the Electron app; the shortcut follows the OS in the browser too.
const macKeyboard = isMac || /Mac/.test(navigator.platform)
export const SIDEBAR_SHORTCUT = macKeyboard ? '⌘B' : 'Ctrl+B'
export const isSidebarShortcut = (e: KeyboardEvent) =>
  (macKeyboard ? e.metaKey && !e.ctrlKey : e.ctrlKey && !e.metaKey) &&
  // Shift/Alt combinations stay with the browser (Ctrl+Shift+B is its bookmarks bar).
  !e.shiftKey &&
  !e.altKey &&
  e.key.toLowerCase() === 'b'
