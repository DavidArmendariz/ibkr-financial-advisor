import { useCallback, useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import * as api from '@/lib/api'
import type { OHLCBar, PlannerSymbol, TradingState } from '@/types'

const STATE_MS = 5_000
const BARS_MS = 30_000

export function errorMessage(e: unknown, fallback: string): string {
  if (isAxiosError(e) && e.response) {
    const data = e.response.data as { detail?: string | { msg?: string }[]; problems?: string[] }
    if (data?.problems?.length) return data.problems.join(' ')
    if (typeof data?.detail === 'string') return data.detail
  }
  return isAxiosError(e) && !e.response ? 'Backend unreachable.' : fallback
}

export function useTrading(symbol: PlannerSymbol) {
  const [state, setState] = useState<TradingState | null>(null)
  const [bars, setBars] = useState<OHLCBar[]>([])

  const refresh = useCallback(async () => {
    try {
      setState(await api.getTradingState())
    } catch {
      // Keep the last state; the page shows the backend as unreachable through the planner.
    }
  }, [])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const load = async () => {
      await refresh()
      if (alive) timer = setTimeout(load, STATE_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [refresh])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    setBars([])
    const load = async () => {
      try {
        const next = await api.getTradingBars(symbol)
        if (alive) setBars(next)
      } catch {
        // The chart keeps its last bars.
      }
      if (alive) timer = setTimeout(load, BARS_MS)
    }
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [symbol])

  return { state, bars, refresh }
}
