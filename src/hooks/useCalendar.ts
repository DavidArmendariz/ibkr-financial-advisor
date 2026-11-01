import { useEffect, useState } from 'react'
import * as api from '@/lib/api'
import type { CalendarState } from '@/types'

const POLL_MS = 60_000

export function useCalendar() {
  const [state, setState] = useState<CalendarState | null>(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getCalendar()
        if (!alive) return
        setState(next)
        setUnreachable(false)
      } catch {
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
