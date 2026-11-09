import { useCallback, useEffect, useRef, useState } from 'react'
import { isAxiosError } from 'axios'
import * as api from '@/lib/api'
import type { FundamentalsErrorCode, FundamentalsLookup } from '@/types'

const LAST_TICKER = 'fundamentals.lastTicker'

export interface FundamentalsError {
  code: FundamentalsErrorCode | 'unreachable'
  message: string
}

function toError(e: unknown): FundamentalsError {
  if (isAxiosError(e) && e.response) {
    const data = e.response.data as { detail?: string; code?: FundamentalsErrorCode }
    return { code: data?.code ?? 'error', message: data?.detail ?? `Request failed (HTTP ${e.response.status})` }
  }
  return { code: 'unreachable', message: 'Backend unreachable.' }
}

function readLast(): string {
  try {
    return localStorage.getItem(LAST_TICKER) ?? ''
  } catch {
    return ''
  }
}

export function useFundamentals() {
  const [data, setData] = useState<FundamentalsLookup | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FundamentalsError | null>(null)
  const [writing, setWriting] = useState(false)
  const [writeError, setWriteError] = useState<FundamentalsError | null>(null)
  const latest = useRef(0)

  const lookup = useCallback(async (ticker: string, refresh = false) => {
    const request = ++latest.current
    setLoading(true)
    setError(null)
    setWriteError(null)
    try {
      const next = await api.getFundamentals(ticker, refresh)
      if (request !== latest.current) return
      setData(next)
      try {
        localStorage.setItem(LAST_TICKER, next.ticker)
      } catch {
        // Remembering the ticker is a convenience only.
      }
    } catch (e) {
      if (request !== latest.current) return
      const err = toError(e)
      setError(err)
      // A different stock's figures would be misleading; a failed refresh keeps the same stock's.
      setData((prev) => (prev && prev.ticker === ticker.trim().toUpperCase() ? prev : null))
    } finally {
      if (request === latest.current) setLoading(false)
    }
  }, [])

  const writeUp = useCallback(async () => {
    if (!data) return
    setWriting(true)
    setWriteError(null)
    try {
      const analysis = await api.writeFundamentalsAnalysis(data.ticker)
      setData((prev) => (prev && prev.ticker === data.ticker ? { ...prev, analysis } : prev))
    } catch (e) {
      setWriteError(toError(e))
    } finally {
      setWriting(false)
    }
  }, [data])

  const initial = useRef(readLast())
  useEffect(() => {
    if (initial.current) lookup(initial.current)
  }, [lookup])

  return { data, loading, error, writing, writeError, lookup, writeUp, initialTicker: initial.current }
}
