import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { AccountSummary, Position } from '@/types'

const POLL_INTERVAL_MS = 15_000

export function usePortfolio(connected: boolean) {
  const [summary, setSummary] = useState<AccountSummary | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    if (!connected) return
    setLoading(true)
    try {
      const [sum, pos] = await Promise.all([
        api.getAccountSummary(),
        api.getPositions(),
      ])
      setSummary(sum)
      setPositions(pos)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch portfolio')
    } finally {
      setLoading(false)
    }
  }, [connected])

  useEffect(() => {
    if (!connected) {
      setSummary(null)
      setPositions([])
      return
    }
    refresh()
    timerRef.current = setInterval(refresh, POLL_INTERVAL_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [connected, refresh])

  return { summary, positions, loading, error, refresh }
}
