import type { ISeriesApi, ISeriesPrimitive, ISeriesPrimitivePaneRenderer, ISeriesPrimitivePaneView, SeriesAttachedParameter, SeriesType, Time } from 'lightweight-charts'
import type { VolumeProfileBars } from '@/types'

const MAX_WIDTH_SHARE = 0.2
const COLORS = { outside: 'rgba(255,255,255,0.07)', value: 'rgba(255,255,255,0.14)', poc: 'rgba(255,255,255,0.3)' }

type Target = Parameters<ISeriesPrimitivePaneRenderer['draw']>[0]

// A primitive draws in the chart's own pane, so bars follow zoom and the price scale.
export class VolumeProfilePrimitive implements ISeriesPrimitive<Time> {
  private series: ISeriesApi<SeriesType, Time> | null = null
  private requestUpdate: (() => void) | null = null
  private profile: VolumeProfileBars | null = null

  private readonly view: ISeriesPrimitivePaneView = {
    zOrder: () => 'bottom',
    renderer: () => ({ draw: (target) => this.draw(target) }),
  }

  attached({ series, requestUpdate }: SeriesAttachedParameter<Time>) {
    this.series = series
    this.requestUpdate = requestUpdate
  }

  detached() {
    this.series = null
    this.requestUpdate = null
  }

  paneViews() {
    return [this.view]
  }

  setProfile(profile: VolumeProfileBars | null) {
    this.profile = profile
    this.requestUpdate?.()
  }

  private draw(target: Target) {
    const { profile, series } = this
    if (!profile || !series || profile.buckets.length === 0) return
    target.useBitmapCoordinateSpace(({ context, bitmapSize, verticalPixelRatio }) => {
      const peak = Math.max(...profile.buckets.map((b) => b.volume))
      const maxWidth = bitmapSize.width * MAX_WIDTH_SHARE
      for (const { price, volume } of profile.buckets) {
        const top = series.priceToCoordinate(price + profile.bucket)
        const bottom = series.priceToCoordinate(price)
        if (top === null || bottom === null) continue
        const y = Math.round(top * verticalPixelRatio)
        const height = Math.round(bottom * verticalPixelRatio) - y
        const width = Math.max(1, (volume / peak) * maxWidth)
        const inValue = price >= profile.value_area_low && price < profile.value_area_high
        context.fillStyle = price === profile.poc ? COLORS.poc : inValue ? COLORS.value : COLORS.outside
        // A 1-pixel gap keeps neighbours apart once buckets are tall enough to show it.
        context.fillRect(bitmapSize.width - width, y, width, Math.max(1, height > 3 ? height - 1 : height))
      }
    })
  }
}
