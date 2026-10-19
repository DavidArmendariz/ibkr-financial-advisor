import { useEffect, useState } from 'react'
import * as api from '@/lib/api'
import type { MacroState } from '@/types'

const POLL_MS = 3_000

export function useMacro() {
  const [state, setState] = useState<MacroState | null>(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    // A request still in flight when the view closes must not schedule another poll.
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getMacroState()
        if (!alive) return
        setState(next)
        setUnreachable(false)
      } catch {
        // Keep the last values on screen; the page marks them as unreachable.
        if (alive) setUnreachable(true)
      }
      if (alive) timer = setTimeout(load, POLL_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  return { state, unreachable }
}
