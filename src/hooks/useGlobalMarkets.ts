import { useEffect, useState } from 'react'
import * as api from '@/lib/api'
import type { GlobalMarketsState } from '@/types'

const POLL_MS = 15_000

export function useGlobalMarkets() {
  const [state, setState] = useState<GlobalMarketsState | null>(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getGlobalMarkets()
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
