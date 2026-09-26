import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { ConnectionStatus } from '@/types'

const POLL_INTERVAL_MS = 10_000

export function useConnection() {
  const [status, setStatus] = useState<ConnectionStatus>({
    connected: false,
    port: null,
    mode: null,
    server_version: null,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await api.getConnectionStatus()
      setStatus(s)
      setError(null)
    } catch {
      setError('Backend unreachable')
    } finally {
      setLoading(false)
    }
  }, [])

  const connect = useCallback(async (mode?: 'paper' | 'live') => {
    setLoading(true)
    setError(null)
    try {
      const result = mode
        ? await api.connectTWS(mode)
        : await api.autoConnect()
      setStatus(result)
      if (!result.connected) setError('Could not connect to TWS / IB Gateway')
    } catch {
      setError('Backend unreachable — make sure the Python server is running')
    } finally {
      setLoading(false)
    }
  }, [])

  const disconnect = useCallback(async () => {
    await api.disconnectTWS()
    setStatus({ connected: false, port: null, mode: null, server_version: null })
  }, [])

  useEffect(() => {
    fetchStatus()
    timerRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [fetchStatus])

  return { status, loading, error, connect, disconnect, refresh: fetchStatus }
}
