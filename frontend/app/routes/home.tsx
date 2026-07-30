import { useChat } from "@chat-adapter/web/react"
import { useEffect, useRef, useState, type FormEvent } from "react"
import type { UIMessage } from "ai"
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router"

import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowUpRight01Icon,
  Download01Icon,
  File01Icon,
  Loading01Icon,
  Tick01Icon,
} from "@hugeicons/core-free-icons"

import { ChatLoader, type ChatLoaderStatus } from "~/components/chat-loader"
import { Markdown } from "~/components/markdown"
import { PromptForm } from "~/components/prompt-form"
import { ScrollArea } from "~/components/ui/scroll-area"
import { useTeam } from "~/lib/team"
import { cn } from "~/lib/utils"

function getMessageText(message: {
  parts?: Array<{ type: string; text?: string }>
}): string {
  return (
    message.parts
      ?.map((part) => (part.type === "text" ? (part.text ?? "") : ""))
      .join("") ?? ""
  )
}

function hasAssistantContent(message?: UIMessage): boolean {
  if (!message) return false
  return Array.isArray(message.parts) && message.parts.length > 0
}

function PlainText({ text }: { text: string }) {
  return <p className="m-0 whitespace-pre-wrap">{text}</p>
}

function ChatHeader({ title }: { title: string | null }) {
  return (
    <div className="flex items-center bg-card p-3">
      <div className="truncate font-heading text-sm font-medium">
        {title?.trim() || "Новый чат"}
      </div>
    </div>
  )
}

interface AgentUpdateData {
  phase: "start" | "step" | "finding" | "end"
  agent: string
  scope?: string[]
  focus?: string
  tool?: string
  target?: string
  status?: "running" | "done" | "error"
  error?: string
  finding?: {
    id?: string
    title?: string
    severity?: string
    confidence?: string
    steps?: string[]
  }
  findings_count?: number
}

function isAgentUpdateData(data: unknown): data is AgentUpdateData {
  return (
    typeof data === "object" &&
    data !== null &&
    "phase" in data &&
    "agent" in data
  )
}

const toolNameLabels: Record<string, string> = {
  run_pentest: "Тест по поиску уязвимостей",
  run_osint: "OSINT-разведка",
  run_research: "Исследование",
}

function formatToolInput(input: Record<string, unknown>) {
  const entries: [string, string][] = []

  for (const [key, value] of Object.entries(input)) {
    if (key === "language" || key === "focus") continue
    if (value === undefined || value === null) continue

    if (Array.isArray(value)) {
      if (value.length > 0) entries.push([key, value.join(", ")])
    } else if (typeof value === "object") {
      entries.push([key, JSON.stringify(value)])
    } else {
      entries.push([key, String(value)])
    }
  }

  return entries
}

function ToolInvocation({ part }: { part: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  const toolName = String(part.type).replace(/^tool-/, "") || "tool"
  const toolLabel = toolNameLabels[toolName] ?? toolName
  const state = String((part.state as string) ?? "input-available")
  const input = (part.input as Record<string, unknown>) ?? {}
  const output = part.output
  const errorText = part.errorText as string | undefined
  const hasOutput =
    state === "output-available" ||
    state === "output-error" ||
    output !== undefined

  const isDone =
    state === "output-available" ||
    (hasOutput && !errorText && state !== "input-available")
  const isError = state === "output-error" || Boolean(errorText)
  const isRunning = !isDone && !isError

  const statusText = isRunning ? `Запущен ${toolLabel}` : toolLabel

  const outputString =
    typeof output === "string"
      ? output
      : output !== undefined
        ? JSON.stringify(output, null, 2)
        : ""

  const inputEntries = formatToolInput(input)

  return (
    <div className="my-2 rounded-xl border border-border bg-muted/40 p-3 text-xs">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          {isDone ? (
            <HugeiconsIcon
              icon={Tick01Icon}
              className="size-3.5 text-primary"
              strokeWidth={2.5}
            />
          ) : (
            <HugeiconsIcon
              icon={Loading01Icon}
              className={cn(
                "size-3.5",
                isError ? "text-destructive" : "text-primary",
                isRunning && "animate-spin"
              )}
              strokeWidth={2}
            />
          )}
          <span
            className={cn(
              "font-medium",
              isError ? "text-destructive" : "text-foreground"
            )}
          >
            {statusText}
          </span>
        </div>
        <span className="text-muted-foreground">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {inputEntries.length > 0 && (
            <div>
              <div className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                Входные параметры
              </div>
              <div className="space-y-1 rounded bg-background p-2 text-[11px]">
                {inputEntries.map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="text-muted-foreground">{key}:</span>
                    <span className="break-all">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {errorText && (
            <div className="rounded bg-destructive/10 p-2 text-destructive">
              {errorText}
            </div>
          )}

          {hasOutput && outputString && (
            <div>
              <div className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                Результат
              </div>
              <div className="max-h-96 overflow-y-auto rounded bg-background p-2">
                {outputString.startsWith("#") ||
                outputString.includes("\n## ") ? (
                  <Markdown>{outputString}</Markdown>
                ) : (
                  <PlainText text={outputString} />
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface AgentGroup {
  agent: string
  start?: AgentUpdateData
  steps: AgentUpdateData[]
  end?: AgentUpdateData
}

function groupAgentParts(parts: unknown[]): AgentGroup[] {
  const groups: AgentGroup[] = []
  let current: AgentGroup | null = null

  for (const part of parts) {
    if (
      !part ||
      typeof part !== "object" ||
      (part as { type?: string }).type !== "data-agent"
    ) {
      continue
    }
    const data = (part as { data?: unknown }).data
    if (!isAgentUpdateData(data)) continue

    if (data.phase === "start") {
      if (current) groups.push(current)
      current = { agent: data.agent, start: data, steps: [] }
    } else if (data.phase === "end") {
      if (current) {
        current.end = data
        groups.push(current)
        current = null
      } else {
        groups.push({ agent: data.agent, end: data, steps: [] })
      }
    } else {
      if (!current || current.agent !== data.agent) {
        if (current) groups.push(current)
        current = { agent: data.agent, steps: [data] }
      } else {
        current.steps.push(data)
      }
    }
  }

  if (current) groups.push(current)
  return groups
}

function AgentCallCard({ group }: { group: AgentGroup }) {
  const [open, setOpen] = useState(true)
  const { agent, start, steps, end } = group
  const isDone = !!end
  const status = isDone
    ? `завершён · ${end?.findings_count ?? 0} находок`
    : "в работе…"

  return (
    <div className="my-2 rounded-xl border border-border bg-muted/40 p-3 text-xs">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="rounded bg-secondary px-1.5 py-0.5 font-medium text-secondary-foreground">
            {agent}
          </span>
          <span className="text-muted-foreground">{status}</span>
        </div>
        <span className="text-muted-foreground">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {start && start.scope && start.scope.length > 0 && (
            <div className="text-muted-foreground">
              Scope: {start.scope.join(", ")}
              {start.focus ? ` · focus: ${start.focus}` : ""}
            </div>
          )}

          {steps.length > 0 && (
            <div className="space-y-1.5">
              {steps.map((step, index) => {
                const key = `${agent}-${index}-${step.tool ?? step.phase}`
                if (step.phase === "finding" && step.finding) {
                  return (
                    <div
                      key={key}
                      className="rounded bg-background p-1.5 text-[11px]"
                    >
                      <div>
                        <span className="font-medium text-destructive">
                          {step.finding.severity ?? "finding"}
                        </span>
                        {": "}
                        {step.finding.title ?? "Находка"}
                        {step.finding.id && (
                          <span className="ml-1 text-muted-foreground">
                            ({step.finding.id})
                          </span>
                        )}
                      </div>
                      {step.finding.steps && step.finding.steps.length > 0 && (
                        <ul className="mt-1 list-disc space-y-0.5 pl-3 text-muted-foreground">
                          {step.finding.steps.map((s, i) => (
                            <li key={`${key}-step-${i}`}>{s}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )
                }

                return (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded bg-background p-1.5 text-[11px]"
                  >
                    <span>
                      {step.tool && (
                        <span className="font-mono text-primary">
                          {step.tool}
                        </span>
                      )}
                      {step.tool && step.target && " · "}
                      {step.target && (
                        <span className="text-muted-foreground">
                          {step.target}
                        </span>
                      )}
                    </span>
                    <span
                      className={cn(
                        "rounded px-1 py-0.5 text-[10px]",
                        step.status === "error"
                          ? "bg-destructive/10 text-destructive"
                          : step.status === "done"
                            ? "bg-primary/10 text-primary"
                            : "bg-muted text-muted-foreground"
                      )}
                    >
                      {step.status === "error"
                        ? "ошибка"
                        : step.status === "done"
                          ? "готово"
                          : "работа"}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {end && (
            <div className="text-[11px] text-muted-foreground">
              Агент {end.agent} завершил работу
              {end.findings_count !== undefined
                ? `, найдено находок: ${end.findings_count}`
                : ""}
              {end.error ? ` · ошибка: ${end.error}` : ""}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function extractReportAttachments(
  parts: unknown[]
): { reportId: string; title: string }[] {
  const seen = new Set<string>()
  const result: { reportId: string; title: string }[] = []

  for (const part of parts) {
    if (!part || typeof part !== "object") continue
    const type = String((part as { type?: string }).type)
    if (!type.startsWith("tool-")) continue

    const output = (part as { output?: unknown }).output
    if (typeof output !== "string") continue

    const idMatch = output.match(/^Report ID:\s*(.+)$/m)
    if (!idMatch) continue
    const reportId = idMatch[1].trim()
    if (seen.has(reportId)) continue
    seen.add(reportId)

    const titleMatch = output.match(/^#\s*(.+)$/m)
    const title = titleMatch
      ? titleMatch[1].trim()
      : "Отчёт о тесте на проникновение"

    result.push({ reportId, title })
  }

  return result
}

function ReportAttachment({
  reportId,
  title,
}: {
  reportId: string
  title: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/40 p-2.5 text-xs">
      <HugeiconsIcon
        icon={File01Icon}
        className="size-5 shrink-0 text-primary"
      />
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{title}</div>
        <div className="truncate text-[10px] text-muted-foreground">
          {reportId}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <Link
          to={`/reports/${reportId}`}
          title="Открыть отчёт"
          className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <HugeiconsIcon icon={ArrowUpRight01Icon} className="size-3.5" />
        </Link>
        <a
          href={`/api/reports/${reportId}/download?format=md`}
          download
          title="Скачать Markdown"
          className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <HugeiconsIcon icon={Download01Icon} className="size-3.5" />
        </a>
      </div>
    </div>
  )
}

function MessageContent({ message }: { message: UIMessage }) {
  const parts = Array.isArray(message.parts) ? message.parts : []

  if (message.role === "user") {
    const text = getMessageText(message)
    return <PlainText text={text} />
  }

  if (parts.length === 0) {
    const text = getMessageText(message)
    return text ? <Markdown>{text}</Markdown> : null
  }

  const agentGroups = groupAgentParts(parts)
  const reportAttachments = extractReportAttachments(parts)

  return (
    <div className="space-y-1">
      {parts.map((part, index) => {
        const type = String((part as { type?: string }).type)

        if (type === "text") {
          const text = String((part as { text?: string }).text ?? "")
          return text ? (
            <Markdown key={`${message.id}-text-${index}`}>{text}</Markdown>
          ) : null
        }

        if (type.startsWith("tool-")) {
          return (
            <ToolInvocation
              key={`${message.id}-tool-${index}`}
              part={part as Record<string, unknown>}
            />
          )
        }

        return null
      })}

      {agentGroups.map((group, index) => (
        <AgentCallCard key={`${message.id}-agent-${index}`} group={group} />
      ))}

      {reportAttachments.length > 0 && (
        <div className="mt-3 space-y-2">
          <div className="text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
            Прикреплённые документы
          </div>
          <div className="space-y-2">
            {reportAttachments.map((attachment) => (
              <ReportAttachment
                key={attachment.reportId}
                reportId={attachment.reportId}
                title={attachment.title}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ChatPanel({ threadId }: { threadId?: string }) {
  const navigate = useNavigate()
  const { team } = useTeam()
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [title, setTitle] = useState<string | null>(null)
  const [chatId, setChatId] = useState(() => threadId ?? crypto.randomUUID())
  const hasNavigatedRef = useRef(false)
  const skipHistoryRef = useRef<string | null>(null)
  const prevThreadIdRef = useRef(threadId)
  const { messages, sendMessage, status, error, setMessages } = useChat({
    api: "/api/chat",
    threadId: chatId,
    onFinish: () => {
      if (!hasNavigatedRef.current && threadId === undefined) {
        hasNavigatedRef.current = true
        navigate(`/chat/${chatId}`, { replace: true })
      }
    },
  })
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const prev = prevThreadIdRef.current
    prevThreadIdRef.current = threadId

    if (threadId === undefined && prev !== undefined) {
      hasNavigatedRef.current = false
      setChatId(crypto.randomUUID())
      return
    }

    if (threadId && threadId !== chatId) {
      setChatId(threadId)
    }
  }, [threadId, chatId])

  const lastAssistantMessage = messages
    .filter((message) => message.role === "assistant")
    .pop()
  const showLoader =
    status !== "ready" &&
    status !== "error" &&
    !hasAssistantContent(lastAssistantMessage as UIMessage | undefined)

  useEffect(() => {
    setTitle(null)

    if (threadId === undefined) {
      skipHistoryRef.current = chatId
      setMessages([])
      setHistoryLoaded(true)
      return
    }

    if (skipHistoryRef.current === threadId) {
      return
    }

    setHistoryLoaded(false)

    fetch(`/api/chat/history?threadId=${encodeURIComponent(threadId)}`)
      .then((response) => response.json())
      .then(
        ({
          messages: history,
          title: historyTitle,
        }: {
          messages: UIMessage[]
          title: string | null
        }) => {
          if (Array.isArray(history) && history.length > 0) {
            setMessages(history)
          }
          setTitle(historyTitle ?? null)
          setHistoryLoaded(true)
        }
      )
      .catch(() => setHistoryLoaded(true))
  }, [threadId, chatId, setMessages])

  useEffect(() => {
    const element = scrollRef.current
    if (element) {
      element.scrollTop = element.scrollHeight
    }
  }, [messages, status])

  const messagesRef = useRef(messages)
  messagesRef.current = messages

  useEffect(() => {
    if (threadId === undefined || status !== "ready") return

    const interval = setInterval(() => {
      fetch(`/api/chat/history?threadId=${encodeURIComponent(threadId)}`)
        .then((response) => response.json())
        .then(
          ({
            messages: history,
            title: historyTitle,
          }: {
            messages: UIMessage[]
            title: string | null
          }) => {
            if (JSON.stringify(history) !== JSON.stringify(messagesRef.current)) {
              if (Array.isArray(history) && history.length > 0) {
                setMessages(history)
              }
              setTitle(historyTitle ?? null)
            }
          }
        )
        .catch(() => {})
    }, 2000)

    return () => clearInterval(interval)
  }, [threadId, status, setMessages, setTitle])

  const hasMessages = messages.length > 0
  const showChatState =
    hasMessages || (threadId !== undefined && !historyLoaded)

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const text = input.trim()
    if (!text || status !== "ready") return

    sendMessage({ text }, { body: { team: team.id, id: chatId } })
    setInput("")
  }

  return (
    <div className="relative h-full w-full max-w-3xl">
      <div
        className={cn(
          "absolute inset-0 flex items-center justify-center transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]",
          showChatState
            ? "pointer-events-none -translate-y-6 scale-95 opacity-0"
            : "translate-y-0 scale-100 opacity-100"
        )}
      >
        <div className="w-full max-w-2xl px-4">
          <PromptForm
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            disabled={status !== "ready"}
            placeholder={
              team.canRunScans
                ? "Что проверим?"
                : "Спроси про репорты (запуск сканов — только Admin/Enterprise)"
            }
          />
        </div>
      </div>

      <div
        className={cn(
          "absolute inset-0 flex flex-col overflow-hidden rounded-[1.75rem] bg-card transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]",
          showChatState
            ? "translate-y-0 scale-100 opacity-100"
            : "pointer-events-none translate-y-6 scale-95 opacity-0"
        )}
      >
        <ChatHeader title={title} />

        <ScrollArea ref={scrollRef} className="flex-1 p-4 pr-2">
          {!historyLoaded ? (
            <div className="flex h-full items-center justify-center">
              <ChatLoader status="submitted" />
            </div>
          ) : (
            <div className="flex flex-col gap-4 py-2">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex",
                    message.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  <div
                    className={cn(
                      "text-sm",
                      message.role === "user"
                        ? "max-w-[80%] rounded-2xl bg-primary px-3 py-2 text-primary-foreground"
                        : "w-full text-foreground"
                    )}
                  >
                    <MessageContent message={message} />
                  </div>
                </div>
              ))}

              {showLoader && (
                <div className="flex justify-start">
                  <ChatLoader status={status as ChatLoaderStatus} />
                </div>
              )}

              {status === "error" && (
                <div className="text-center text-sm text-destructive">
                  Ошибка: {error?.message ?? "Не удалось получить ответ"}
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        <div className="p-4">
          <PromptForm
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            disabled={status !== "ready" || !historyLoaded}
            placeholder={
              team.canRunScans
                ? "Напиши запрос (Enter — отправить, Shift+Enter — новая строка)"
                : "Спроси про репорты (запуск сканов — только Admin/Enterprise)"
            }
          />
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const params = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [threadId, setThreadId] = useState<string | null>(() => {
    const urlThread = params.threadId ?? searchParams.get("thread")
    if (urlThread) return urlThread
    if (typeof window === "undefined") return null
    if (location.pathname === "/") return localStorage.getItem("threadId")
    return null
  })

  useEffect(() => {
    if (typeof window === "undefined") return

    const urlThread = params.threadId ?? searchParams.get("thread")

    if (urlThread) {
      localStorage.setItem("threadId", urlThread)
      if (searchParams.get("thread")) {
        navigate(`/chat/${urlThread}`, { replace: true })
      } else {
        setThreadId(urlThread)
      }
      return
    }

    if (location.pathname === "/chat") {
      setThreadId(null)
      return
    }

    if (location.pathname === "/") {
      const stored = localStorage.getItem("threadId")
      if (stored) {
        navigate(`/chat/${stored}`, { replace: true })
      } else {
        navigate("/chat", { replace: true })
      }
    }
  }, [params.threadId, searchParams, navigate, location.pathname])

  return <ChatPanel threadId={threadId ?? undefined} />
}
