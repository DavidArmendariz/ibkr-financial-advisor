import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { ConnectionStatus } from '@/types'

const POLL_INTERVAL_MS = 10_000

const DISCONNECTED: ConnectionStatus = {
  connected: false,
  port: null,
  mode: null,
  server_version: null,
}

export function useConnection() {
  const [status, setStatus] = useState<ConnectionStatus>(DISCONNECTED)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Auto-connect keeps retrying while disconnected, so the app connects on its
  // own once TWS is started (or logs back in after its daily restart). It only
  // ever tries the paper account; live requires an explicit click. A manual
  // disconnect pauses it until the user connects again.
  const [autoConnect, setAutoConnect] = useState(true)
  const autoConnectRef = useRef(true)
  const statusRef = useRef<ConnectionStatus>(DISCONNECTED)
  const busyRef = useRef(false)

  const applyStatus = useCallback((s: ConnectionStatus) => {
    statusRef.current = s
    setStatus(s)
  }, [])

  const setAutoConnectEnabled = useCallback((enabled: boolean) => {
    autoConnectRef.current = enabled
    setAutoConnect(enabled)
  }, [])

  const fetchStatus = useCallback(async () => {
    try {
      applyStatus(await api.getConnectionStatus())
      setError(null)
      return true
    } catch {
      setError('Backend unreachable')
      return false
    }
  }, [applyStatus])

  const connect = useCallback(
    async (mode?: 'paper' | 'live', { background = false } = {}) => {
      if (busyRef.current) return
      busyRef.current = true
      if (!background) {
        setLoading(true)
        setAutoConnectEnabled(true)
      }
      try {
        const result = mode ? await api.connectTWS(mode) : await api.autoConnect()
        if (result.connected) {
          await fetchStatus()
        } else {
          applyStatus(DISCONNECTED)
          setError('Could not connect to TWS / IB Gateway')
        }
      } catch {
        setError('Backend unreachable — make sure the Python server is running')
      } finally {
        busyRef.current = false
        if (!background) setLoading(false)
      }
    },
    [applyStatus, fetchStatus, setAutoConnectEnabled],
  )

  const disconnect = useCallback(async () => {
    setAutoConnectEnabled(false)
    await api.disconnectTWS()
    applyStatus(DISCONNECTED)
  }, [applyStatus, setAutoConnectEnabled])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    // Each check is scheduled after the previous one finishes, since an
    // auto-connect attempt can take several seconds when TWS isn't reachable.
    const tick = async (initial: boolean) => {
      if (!busyRef.current) {
        const backendUp = await fetchStatus()
        if (backendUp && !statusRef.current.connected && autoConnectRef.current && !cancelled) {
          await connect('paper', { background: !initial })
        }
      }
      if (initial) setLoading(false)
      if (!cancelled) timer = setTimeout(() => tick(false), POLL_INTERVAL_MS)
    }

    tick(true)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [connect, fetchStatus])

  return { status, loading, error, autoConnect, connect, disconnect, refresh: fetchStatus }
}
