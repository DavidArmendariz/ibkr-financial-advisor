import { useCallback, useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import * as api from '@/lib/api'
import type { OpenOrder } from '@/types'

const POLL_MS = 15_000

export type OpenOrdersStatus = 'loading' | 'ready' | 'refused' | 'disconnected' | 'unreachable'

export function useOpenOrders() {
  const [orders, setOrders] = useState<OpenOrder[]>([])
  const [status, setStatus] = useState<OpenOrdersStatus>('loading')
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    // A request still in flight when the view closes must not schedule another poll.
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      setLoading(true)
      let refused = false
      try {
        const next = await api.getOpenOrders()
        if (!alive) return
        refused = !next.available
        setOrders(next.orders)
        setStatus(refused ? 'refused' : 'ready')
      } catch (e) {
        if (!alive) return
        // Keep the last orders on screen; the page says they may be out of date.
        setStatus(isAxiosError(e) && e.response?.status === 503 ? 'disconnected' : 'unreachable')
      }
      setLoading(false)
      // Each refused request can raise a pop-up in TWS, so only the user retries it.
      if (!refused) timer = setTimeout(load, POLL_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [attempt])

  const refresh = useCallback(() => setAttempt((n) => n + 1), [])

  return { orders, status, loading, refresh }
}
