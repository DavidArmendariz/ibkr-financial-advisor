import { useCallback, useEffect, useState } from 'react'
import * as api from '@/lib/api'
import type { FilledOrder } from '@/types'

const POLL_MS = 15_000

export function useFilledOrders() {
  const [orders, setOrders] = useState<FilledOrder[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'refused' | 'failed'>('loading')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getFilledOrders()
        if (!alive) return
        setOrders(next.orders)
        setStatus(next.available ? 'ready' : 'refused')
      } catch {
        // The open orders above already report a lost connection or backend.
        if (alive) setStatus((now) => (now === 'loading' ? 'failed' : now))
      }
      if (alive) timer = setTimeout(load, POLL_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [attempt])

  const refresh = useCallback(() => setAttempt((n) => n + 1), [])

  return { orders, status, refresh }
}
