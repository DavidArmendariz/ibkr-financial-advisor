import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-1.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">{children}</div>
    </section>
  )
}

export function M2Explainer() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">About M2</CardTitle>
      </CardHeader>
      <CardContent className="flex max-w-3xl flex-col gap-5">
        <Section title="What M2 is">
          <p>
            M2 is the Federal Reserve's broad measure of the money held by US households and businesses: money that can be spent right away, plus
            savings that can be turned into spending quickly. The Fed publishes it monthly in its H.6 release, about four weeks after the month ends.
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <span className="text-foreground">M1</span>: currency in circulation, checking accounts, and, since May 2020, savings accounts.
            </li>
            <li>
              <span className="text-foreground">Plus</span> small time deposits (CDs under $100,000) and balances in retail money market funds.
            </li>
            <li>
              <span className="text-foreground">Not included</span>: stocks, bonds and Treasury bills, institutional money market funds, and money held in
              retirement accounts.
            </li>
          </ul>
        </Section>

        <Section title="M2 vs. M1">
          <p>
            In May 2020 the Fed reclassified savings deposits as M1, which made M1 more than triple in a single month. M2 already included savings, so it
            didn't change. That makes M2 the steadier series for comparing today with the past.
          </p>
        </Section>

        <Section title="Why it matters for markets">
          <p>
            <span className="text-foreground">Liquidity.</span> M2 grows when banks lend, when the Fed buys bonds (quantitative easing), and when the
            government spends more than it collects. Fast growth means more cash on hand looking for a home, in spending and in assets. Slow or negative
            growth means tighter conditions, often when the Fed is raising rates or shrinking its balance sheet.
          </p>
          <p>
            <span className="text-foreground">Inflation.</span> More money chasing the same goods can push prices up, usually with a lag of a year or more.
            M2 grew about 27% in the year to February 2021, and inflation peaked in 2022. The link is loose, though: from the 1990s to 2019, M2 growth
            said little about inflation.
          </p>
          <p>
            <span className="text-foreground">Valuations.</span> Plentiful liquidity tends to support higher price-to-earnings multiples, especially for
            long-duration, high-beta stocks like semiconductors, and leveraged funds like SOXL amplify those moves. When liquidity drains, those stocks
            usually feel it first.
          </p>
        </Section>

        <Section title="How to read the charts">
          <p>
            <span className="text-foreground">Level.</span> M2 rises almost every year as the economy and prices grow, so the line going up is normal. Look
            at its slope: a steepening line means money is growing faster than usual, and a flat or falling line is rare. M2 peaked at $21.8T in March
            2022 and then fell, its first sustained decline since the series began in 1959.
          </p>
          <p>
            <span className="text-foreground">Growth vs. a year earlier.</span> This is the line to watch. Since 1960 the median is about 6.5% a year
            (about 5.7% from 1990 to 2019). Readings above 10% are unusual: the 1970s, the early 1980s, 2001, 2009, 2012, and 2020–22. Shrinking
            (red) happened only once in the data, from December 2022 to February 2024. A turn from shrinking back to growing, or a sharp acceleration,
            is the kind of change worth noticing.
          </p>
        </Section>

        <Section title="Limits">
          <ul className="list-disc space-y-1 pl-5">
            <li>It lags: each month arrives about four weeks later, and past months get revised.</li>
            <li>How fast money changes hands (velocity) shifts over time, so the same M2 growth can mean different things in different decades.</li>
            <li>It's US-only. Global liquidity, the Fed's balance sheet, credit spreads and real interest rates matter too.</li>
            <li>
              <span className="text-foreground">It gives context, not timing signals.</span> Markets can rise while M2 shrinks and fall while it grows for
              months at a time. Use it to understand the backdrop, not to time trades.
            </li>
          </ul>
        </Section>
      </CardContent>
    </Card>
  )
}
