'use strict'

const { Notification } = require('electron')
const WebSocket = require('ws')

const RECONNECT_MAX_MS = 30_000

const CATEGORY_LABELS = { volume: 'Volume', technical: 'Technical' }

const fmt = (n) => (typeof n === 'number' ? n.toFixed(2) : '–')

function describe(signal) {
  const i = signal.indicators || {}
  const llm = signal.llm || {}
  const title = `${signal.symbol} ${signal.signal_type.replace(/_/g, ' ')} @ ${fmt(signal.price)}`
  const emaLabel = signal.ema_periods ? `EMA ${signal.ema_periods.join('/')}:` : 'EMA'
  const values = `VWAP ${fmt(i.vwap)} · ${emaLabel} ${fmt(i.ema_fast)}/${fmt(i.ema_slow)} · RVOL ${fmt(i.rvol)}x${typeof i.rsi === 'number' ? ` · RSI ${fmt(i.rsi)}` : ''}`
  const verdict =
    llm.action === 'take'
      ? `LLM ${Math.round((llm.confidence || 0) * 100)}%: ${llm.reason}`
      : `Unfiltered${llm.reason ? ` (${llm.reason})` : ''}`
  const category = CATEGORY_LABELS[signal.category]
  const lines = [category && `${category} trigger`, values, verdict].filter(Boolean)
  return { title, body: lines.join('\n') }
}

const ET_TIME = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false })
const TIMING_LABELS = { before_open: 'before the open', after_close: 'after the close' }

function describeCalendar({ alert, event }) {
  const when = event.at ? `${ET_TIME.format(new Date(event.at))} ET` : TIMING_LABELS[event.timing] ?? 'time not confirmed'
  const lead = alert === 'soon' ? 'In 30 minutes' : 'Tomorrow'
  return { title: event.name, body: `${lead}, ${when}` }
}

// The main process subscribes itself (not the renderer) so alerts still arrive
// while the window is closed and the app lives in the dock.
function startSignalNotifications({ url, onClick, onCalendarClick }) {
  let socket = null
  let stopped = false
  let delay = 1000
  let timer = null
  // macOS drops click handlers of notifications that get garbage-collected.
  const live = new Set()

  const show = (signal) => {
    if (!Notification.isSupported()) return
    const notification = new Notification(describe(signal))
    live.add(notification)
    notification.on('click', () => onClick(signal))
    notification.on('close', () => live.delete(notification))
    notification.show()
  }

  const showCalendar = (update) => {
    if (!Notification.isSupported()) return
    const notification = new Notification(describeCalendar(update))
    live.add(notification)
    notification.on('click', () => onCalendarClick?.())
    notification.on('close', () => live.delete(notification))
    notification.show()
  }

  const connect = () => {
    if (stopped) return
    socket = new WebSocket(url)
    socket.on('open', () => {
      delay = 1000
    })
    socket.on('message', (data) => {
      let event
      try {
        event = JSON.parse(data.toString())
      } catch {
        return
      }
      if (event.type === 'signal' && event.notify) show(event.signal)
      if (event.type === 'calendar') showCalendar(event)
    })
    socket.on('close', () => {
      if (stopped) return
      timer = setTimeout(connect, delay)
      delay = Math.min(delay * 2, RECONNECT_MAX_MS)
    })
    socket.on('error', () => {}) // 'close' follows and schedules the reconnect
  }

  connect()
  return () => {
    stopped = true
    clearTimeout(timer)
    socket?.close()
  }
}

module.exports = { startSignalNotifications, describe, describeCalendar }
