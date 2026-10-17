import { useCallback, useState } from 'react'

const STORAGE_KEY = 'deltaadvisor.sidebarCollapsed'

// Read synchronously so the first render already has the right layout (no flash
// of the sidebar on launch). Storage can be blocked; fall back to shown.
function load(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

export function useSidebarCollapsed() {
  const [collapsed, setCollapsed] = useState(load)

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(STORAGE_KEY, String(next))
      } catch {
        // Not remembered across launches, but the toggle still works.
      }
      return next
    })
  }, [])

  return { collapsed, toggle }
}
