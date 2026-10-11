import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '@/lib/api'
import type { GammaSettings, GammaState } from '@/types'

const POLL_BUSY_MS = 2_000
const POLL_IDLE_MS = 30_000

export function useGamma() {
  const [state, setState] = useState<GammaState | null>(null)
  const [unreachable, setUnreachable] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>()

  const load = useCallback(async () => {
    clearTimeout(timer.current)
    let busy = false
    try {
      const next = await api.getGammaState()
      setState(next)
      setUnreachable(false)
      busy = next.refreshing
    } catch {
      setUnreachable(true)
    }
    timer.current = setTimeout(load, busy ? POLL_BUSY_MS : POLL_IDLE_MS)
  }, [])

  useEffect(() => {
    load()
    return () => clearTimeout(timer.current)
  }, [load])

  const refresh = useCallback(async () => {
    setState(await api.refreshGamma())
    load()
  }, [load])

  const saveSettings = useCallback(
    async (values: Partial<GammaSettings>) => {
      const saved = await api.updateGammaSettings(values)
      load()
      return saved
    },
    [load],
  )

  return { state, unreachable, refresh, saveSettings }
}
