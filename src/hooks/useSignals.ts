import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { SignalLive, SignalRecord, SignalSettings, SignalStatus } from '@/types'

const HISTORY_SIZE = 50
const RECONNECT_MAX_MS = 15_000

export function useSignals() {
  const [status, setStatus] = useState<SignalStatus | null>(null)
  const [live, setLive] = useState<SignalLive | null>(null)
  const [history, setHistory] = useState<SignalRecord[]>([])
  const [settings, setSettings] = useState<SignalSettings | null>(null)
  const [socketOpen, setSocketOpen] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let stopped = false
    let delay = 1000
    let timer: ReturnType<typeof setTimeout> | undefined

    const connect = () => {
      if (stopped) return
      const socket = api.createSignalsSocket()
      socketRef.current = socket
      socket.onopen = () => {
        delay = 1000
        setSocketOpen(true)
      }
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'init') {
          setStatus(data.status)
          setLive(data.live)
          setHistory(data.history)
          setSettings(data.settings)
        } else if (data.type === 'status') {
          setStatus(data.status)
        } else if (data.type === 'live') {
          setLive(data.live)
        } else if (data.type === 'settings') {
          setSettings(data.settings)
        } else if (data.type === 'signal') {
          setHistory((prev) => [data.signal, ...prev].slice(0, HISTORY_SIZE))
        }
      }
      socket.onclose = () => {
        setSocketOpen(false)
        if (stopped) return
        timer = setTimeout(connect, delay)
        delay = Math.min(delay * 2, RECONNECT_MAX_MS)
      }
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(timer)
      socketRef.current?.close()
    }
  }, [])

  const saveSettings = useCallback(async (values: Partial<SignalSettings>) => {
    const saved = await api.updateSignalSettings(values)
    setSettings(saved)
    return saved
  }, [])

  return { status, live, history, settings, socketOpen, saveSettings }
}
