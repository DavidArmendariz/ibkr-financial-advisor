import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { SignalHistoryRecord } from '@/types'

const POLL_MS = 15_000

export function useSignalHistory(type: string | null) {
  const [signals, setSignals] = useState<SignalHistoryRecord[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [unreachable, setUnreachable] = useState(false)
  const activeType = useRef(type)

  useEffect(() => {
    activeType.current = type
    setSignals([])
    setNextCursor(null)
    setLoaded(false)
    let alive = true
    let first = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const page = await api.getSignalHistory(type)
        if (!alive) return
        // Older pages stay loaded: a poll only adds rows that weren't there yet.
        setSignals((prev) => {
          const known = new Set(prev.map((s) => s.id))
          return [...page.signals.filter((s) => !known.has(s.id)), ...prev]
        })
        if (first) setNextCursor(page.next_cursor)
        first = false
        setLoaded(true)
        setUnreachable(false)
      } catch {
        if (!alive) return
        setUnreachable(true)
      }
      timer = setTimeout(load, POLL_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [type])

  const loadOlder = useCallback(async () => {
    if (!nextCursor) return
    setLoadingOlder(true)
    try {
      const page = await api.getSignalHistory(type, nextCursor)
      if (activeType.current !== type) return
      setSignals((prev) => {
        const known = new Set(prev.map((s) => s.id))
        return [...prev, ...page.signals.filter((s) => !known.has(s.id))]
      })
      setNextCursor(page.next_cursor)
      setUnreachable(false)
    } catch {
      setUnreachable(true)
    } finally {
      setLoadingOlder(false)
    }
  }, [type, nextCursor])

  return { signals, loaded, unreachable, hasOlder: nextCursor !== null, loadingOlder, loadOlder }
}
