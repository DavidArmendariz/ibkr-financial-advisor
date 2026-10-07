import { memo } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Element } from 'hast'
import { BarChart3 } from 'lucide-react'
import { ChartBlock, parseChartSpec } from './ChartBlock'
import { PriceChartBlock, parsePriceChartSpec } from './PriceChartBlock'

interface Props {
  content: string
  // While a reply streams in, a chart block is incomplete JSON until its fence closes.
  streaming?: boolean
}

// Built once at module level: if these were recreated on every render, React
// would see new component types and remount every chart (refetching price data)
// whenever anything above re-rendered, such as a keystroke in the chat input.
function makeComponents(streaming: boolean): Components {
  return {
    pre({ node, children }) {
      const code = node?.children[0]
      if (code && code.type === 'element' && code.tagName === 'code') {
        const lang = codeLanguage(code)
        if (lang === 'chart' || lang === 'price-chart') {
          const source = codeText(code)
          if (lang === 'chart') {
            const spec = parseChartSpec(source)
            if (spec) return <ChartBlock spec={spec} />
          } else {
            const spec = parsePriceChartSpec(source)
            if (spec) return <PriceChartBlock {...spec} />
          }
          if (streaming) return <ChartPlaceholder />
        }
      }
      return <pre className="my-2 overflow-x-auto rounded-md bg-black/30 p-3 font-mono text-xs">{children}</pre>
    },
    code({ children, className }) {
      return <code className={className ?? 'rounded bg-black/30 px-1 font-mono text-xs'}>{children}</code>
    },
    a({ href, children }) {
      // setWindowOpenHandler in the main process sends new-window links to the system browser
      return (
        <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:opacity-80">
          {children}
        </a>
      )
    },
    table({ children }) {
      return (
        <div className="my-2 overflow-x-auto">
          <table className="w-full border-collapse text-xs">{children}</table>
        </div>
      )
    },
    th({ children, style }) {
      return (
        <th style={style} className="border-b border-border px-2 py-1.5 text-left font-semibold">
          {children}
        </th>
      )
    },
    td({ children, style }) {
      return (
        <td style={style} className="border-b border-border px-2 py-1.5 tabular-nums">
          {children}
        </td>
      )
    },
  }
}

const COMPONENTS = makeComponents(false)
const STREAMING_COMPONENTS = makeComponents(true)

export const Markdown = memo(function Markdown({ content, streaming = false }: Props) {
  return (
    <div className="space-y-2 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_h1]:mt-3 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-semibold [&_h3]:mt-2 [&_h3]:font-semibold [&_hr]:border-border [&_li]:my-0.5 [&_ol]:ml-5 [&_ol]:list-decimal [&_ul]:ml-5 [&_ul]:list-disc">
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={streaming ? STREAMING_COMPONENTS : COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  )
})

const REMARK_PLUGINS = [remarkGfm]

function codeLanguage(code: Element): string | undefined {
  const classes = code.properties?.className
  if (!Array.isArray(classes)) return undefined
  const lang = classes.find((c) => typeof c === 'string' && c.startsWith('language-'))
  return typeof lang === 'string' ? lang.slice('language-'.length) : undefined
}

function codeText(code: Element): string {
  return code.children.map((c) => (c.type === 'text' ? c.value : '')).join('')
}

function ChartPlaceholder() {
  return (
    <div className="my-3 flex h-24 w-[560px] max-w-full items-center justify-center gap-2 rounded-lg border border-border text-xs text-muted-foreground">
      <BarChart3 className="h-4 w-4 animate-pulse" />
      Drawing chart…
    </div>
  )
}
