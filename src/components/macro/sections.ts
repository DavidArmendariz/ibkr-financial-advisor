export type MacroCardLayout = string | { label: string; futures: string; spot: string }

export const MACRO_SECTIONS: { label: string; cards: MacroCardLayout[] }[] = [
  {
    label: 'Equity indexes',
    cards: [
      { label: 'S&P 500', futures: 'es', spot: 'spx' },
      { label: 'Nasdaq 100', futures: 'nq', spot: 'ndx' },
      { label: 'Dow Jones', futures: 'dow', spot: 'dji' },
    ],
  },
  { label: 'Rates & volatility', cards: ['us10y', 'vix'] },
  { label: 'Commodities & currency', cards: ['crude', 'gold', 'usdcop'] },
]
