import { useCallback, useEffect, useState } from 'react'
import * as api from '@/lib/api'
import type { RotationSettings, RotationState } from '@/types'

// Readings change once a session, so this only picks up a finished refresh.
const POLL_MS = 60_000

export function useRotation() {
  const [state, setState] = useState<RotationState | null>(null)
  const [unreachable, setUnreachable] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const next = await api.getRotation()
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

  const update = useCallback(async (values: Partial<RotationSettings>) => {
    // Applied right away so the graph follows the control; the save only remembers it.
    setState((s) => (s ? { ...s, settings: { ...s.settings, ...values } } : s))
    try {
      const settings = await api.updateRotationSettings(values)
      setState((s) => (s ? { ...s, settings } : s))
      setSaveError(null)
    } catch {
      setSaveError("Couldn't save this choice, so it won't be remembered next launch.")
    }
  }, [])

  return { state, unreachable, saveError, update }
}
