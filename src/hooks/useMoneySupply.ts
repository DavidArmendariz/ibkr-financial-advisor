import { useCallback, useEffect, useState } from 'react'
import * as api from '@/lib/api'
import type { MoneySupplyRange, MoneySupplyState } from '@/types'

const POLL_MS = 60_000
const RANGE_KEY = 'money-supply:range'
const RANGES: MoneySupplyRange[] = ['5y', '10y', '25y', 'all']

function storedRange(): MoneySupplyRange {
  try {
    const value = localStorage.getItem(RANGE_KEY)
    return RANGES.includes(value as MoneySupplyRange) ? (value as MoneySupplyRange) : '10y'
  } catch {
    return '10y'
  }
}

export function useMoneySupply() {
  const [state, setState] = useState<MoneySupplyState | null>(null)
  const [unreachable, setUnreachable] = useState(false)
  const [range, setRangeState] = useState<MoneySupplyRange>(storedRange)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getMoneySupply()
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

  const setRange = useCallback((next: MoneySupplyRange) => {
    setRangeState(next)
    try {
      localStorage.setItem(RANGE_KEY, next)
    } catch {
      // Private window or blocked storage: the choice just isn't remembered.
    }
  }, [])

  return { state, unreachable, range, setRange }
}
