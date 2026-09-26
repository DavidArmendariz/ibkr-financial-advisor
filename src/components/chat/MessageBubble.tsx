import { Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types'

interface Props {
  message: ChatMessage
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3 px-4 py-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground',
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
          isUser
            ? 'rounded-tr-sm bg-primary text-primary-foreground'
            : 'rounded-tl-sm bg-secondary text-secondary-foreground',
        )}
      >
        <MarkdownContent content={message.content} />
      </div>
    </div>
  )
}

export function StreamingBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-3 px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
        <Bot className="h-4 w-4" />
      </div>
      <div className="max-w-[78%] rounded-2xl rounded-tl-sm bg-secondary px-4 py-3 text-sm leading-relaxed text-secondary-foreground">
        {content ? (
          <MarkdownContent content={content} />
        ) : (
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
          </span>
        )}
      </div>
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (line.startsWith('```')) {
      const langEnd = lines.indexOf('```', i + 1)
      const codeLines = langEnd > -1 ? lines.slice(i + 1, langEnd) : lines.slice(i + 1)
      elements.push(
        <pre key={i} className="my-2 overflow-x-auto rounded-md bg-black/30 p-3 text-xs font-mono">
          {codeLines.join('\n')}
        </pre>,
      )
      i = langEnd > -1 ? langEnd + 1 : lines.length
    } else if (line.startsWith('### ')) {
      elements.push(<h3 key={i} className="mt-3 mb-1 font-semibold">{inlineFormat(line.slice(4))}</h3>)
      i++
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={i} className="mt-3 mb-1 text-base font-semibold">{inlineFormat(line.slice(3))}</h2>)
      i++
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(<li key={i} className="ml-4 list-disc">{inlineFormat(line.slice(2))}</li>)
      i++
    } else if (line.trim() === '') {
      elements.push(<br key={i} />)
      i++
    } else {
      elements.push(<p key={i} className="leading-relaxed">{inlineFormat(line)}</p>)
      i++
    }
  }

  return <div className="space-y-0.5">{elements}</div>
}

function inlineFormat(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="rounded bg-black/30 px-1 font-mono text-xs">{part.slice(1, -1)}</code>
    }
    return part
  })
}
