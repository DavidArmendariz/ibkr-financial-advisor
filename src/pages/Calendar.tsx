import { AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useCalendar } from '@/hooks/useCalendar'
import type { CalendarEventRecord, CalendarSource } from '@/types'

const TIMINGS = { before_open: 'Before open', after_close: 'After close' }
const MISSING_KEY: Record<string, string> = {
  fred: 'Add a free FRED key in Settings to see CPI, jobs, GDP and other releases.',
  finnhub: 'Add a free Finnhub key in Settings to see chip earnings.',
}
const etTime = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false })

function dayLabel(day: string) {
  return new Date(`${day}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
}

function eventTime(event: CalendarEventRecord) {
  if (event.at) return `${etTime.format(new Date(event.at))} ET`
  return event.timing ? TIMINGS[event.timing] : 'Time not confirmed'
}

function groupByDay(events: CalendarEventRecord[]) {
  const days = new Map<string, CalendarEventRecord[]>()
  for (const event of events) days.set(event.day, [...(days.get(event.day) ?? []), event])
  return [...days.entries()]
}

function SourceNote({ source, onOpenSettings }: { source: CalendarSource; onOpenSettings: () => void }) {
  if (source.error) {
    const partial = source.error.includes("doesn't cover")
    const updated = source.updated_at && !partial ? ` Showing saved events from ${new Date(source.updated_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}.` : ''
    return (
      <p className="flex items-start gap-1.5 text-xs text-red-400">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          {source.error}.{updated}
        </span>
      </p>
    )
  }
  if (source.configured) return null
  return (
    <p className="text-xs text-amber-400">
      {MISSING_KEY[source.key]}{' '}
      <button type="button" onClick={onOpenSettings} className="no-drag underline">
        Open Settings
      </button>
    </p>
  )
}

export function CalendarPage({ onOpenSettings }: { onOpenSettings: () => void }) {
  const { state, unreachable } = useCalendar()
  const groups = groupByDay(state?.events ?? [])
  const fetched = state?.sources.some((s) => s.updated_at)

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-lg font-semibold">Calendar</h1>
          <p className="text-sm text-muted-foreground">Upcoming economic releases and chip earnings for the next 30 days. Times are in ET.</p>
        </div>

        {unreachable && <p className="text-sm text-red-400">Backend unreachable. This list may be out of date.</p>}
        {state?.sources.map((source) => <SourceNote key={source.key} source={source} onOpenSettings={onOpenSettings} />)}
        {state && groups.length === 0 && (
          <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
            <span>{fetched ? 'No events in the next 30 days' : 'Loading events…'}</span>
            {!fetched && (
              <Button variant="outline" size="sm" onClick={onOpenSettings} className="no-drag">
                Open Settings
              </Button>
            )}
          </div>
        )}

        {groups.map(([day, events]) => (
          <section key={day} aria-label={dayLabel(day)} className="flex flex-col gap-1.5">
            <h2 className="text-sm font-medium">{dayLabel(day)}</h2>
            <ul className="overflow-hidden rounded-lg border border-border">
              {events.map((event) => (
                <li key={event.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-3 py-2 text-sm last:border-0">
                  <span className="w-24 shrink-0 tabular-nums text-muted-foreground">{eventTime(event)}</span>
                  <span className="font-medium">{event.name}</span>
                  <Badge variant="secondary" className="text-[10px] capitalize">
                    {event.category}
                  </Badge>
                  {event.importance === 'high' && (
                    <Badge variant="outline" className="text-[10px]">
                      High importance
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </ScrollArea>
  )
}
