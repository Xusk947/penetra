import type { UIMessage } from "ai"
import type { ActionFunctionArgs } from "react-router"

import { getLocaleFromRequest, translate, type Locale } from "~/lib/i18n"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

function buildChatTitle(messages: UIMessage[], locale: Locale): string {
  const firstUser = messages.find((message) => message.role === "user")
  if (!firstUser) return translate(locale, "chat.header.new")

  const text = extractTextFromUIMessage(firstUser).replace(/\s+/g, " ").trim()
  if (!text) return translate(locale, "chat.header.new")
  if (text.length <= 50) return text
  return `${text.slice(0, 47)}…`
}

function extractTextFromUIMessage(message: UIMessage): string {
  const parts = (message as { parts?: unknown }).parts
  if (Array.isArray(parts)) {
    return parts
      .filter((part) => part && typeof part === "object" && "type" in part)
      .map((part) =>
        (part as { type: string; text?: unknown }).type === "text"
          ? String((part as { text?: unknown }).text ?? "")
          : ""
      )
      .join("")
  }

  const content = (message as { content?: unknown }).content
  return contentToString(content) ?? ""
}

function contentToString(content: unknown): string | null {
  if (typeof content === "string") return content
  if (Array.isArray(content)) {
    return content
      .map((item) =>
        item && typeof item === "object" && "text" in item
          ? String((item as { text: unknown }).text)
          : String(item)
      )
      .join("")
  }
  return null
}

function createDataStream(text: string) {
  const encoder = new TextEncoder()
  const messageId = crypto.randomUUID()
  const blockId = `text_${crypto.randomUUID().slice(0, 8)}`

  const events = [
    JSON.stringify({ type: "start", messageId }),
    JSON.stringify({ type: "text-start", id: blockId }),
    JSON.stringify({ type: "text-delta", id: blockId, delta: text }),
    JSON.stringify({ type: "text-end", id: blockId }),
    JSON.stringify({ type: "finish" }),
    "[DONE]",
  ]

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${event}\n\n`))
      }
      controller.close()
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "x-vercel-ai-ui-message-stream": "v1",
    },
  })
}

function createLangGraphStreamTransformer() {
  const decoder = new TextDecoder()
  const encoder = new TextEncoder()
  const messageId = crypto.randomUUID()
  const textBlockId = `text_${crypto.randomUUID().slice(0, 8)}`

  let buffer = ""
  let lastContent = ""
  let errored = false
  let textStarted = false
  const emittedToolCalls = new Set<string>()
  const emittedToolOutputs = new Set<string>()

  function enqueueEvent(
    controller: TransformStreamDefaultController<Uint8Array>,
    payload: object | string
  ) {
    const data = typeof payload === "string" ? payload : JSON.stringify(payload)
    controller.enqueue(encoder.encode(`data: ${data}\n\n`))
  }

  function ensureTextStart(
    controller: TransformStreamDefaultController<Uint8Array>
  ) {
    if (!textStarted) {
      enqueueEvent(controller, { type: "text-start", id: textBlockId })
      textStarted = true
    }
  }

  function emitDelta(
    controller: TransformStreamDefaultController<Uint8Array>,
    content: string
  ) {
    if (!content || content === lastContent) return

    ensureTextStart(controller)

    if (lastContent && content.startsWith(lastContent)) {
      const delta = content.slice(lastContent.length)
      enqueueEvent(controller, {
        type: "text-delta",
        id: textBlockId,
        delta,
      })
    } else {
      enqueueEvent(controller, {
        type: "text-delta",
        id: textBlockId,
        delta: content,
      })
    }

    lastContent = content
  }

  function processMessagesEvent(
    controller: TransformStreamDefaultController<Uint8Array>,
    data: string
  ) {
    let parsed: unknown
    try {
      parsed = JSON.parse(data)
    } catch {
      return
    }

    if (!Array.isArray(parsed)) return

    for (const message of parsed) {
      if (!message || typeof message !== "object") continue

      const type =
        (message as { type?: unknown }).type ??
        (message as { role?: unknown }).role

      if (type === "ai" || type === "assistant") {
        const text = contentToString((message as { content: unknown }).content)
        if (text) emitDelta(controller, text)

        const toolCalls = (message as { tool_calls?: unknown }).tool_calls
        if (Array.isArray(toolCalls)) {
          for (const toolCall of toolCalls) {
            if (!toolCall || typeof toolCall !== "object") continue
            const toolCallId = String(
              (toolCall as { id?: unknown }).id ?? crypto.randomUUID()
            )
            const toolName = String(
              (toolCall as { name?: unknown }).name ??
                (toolCall as { toolName?: unknown }).toolName ??
                "tool"
            )
            const input =
              (toolCall as { args?: unknown }).args ??
              (toolCall as { input?: unknown }).input ??
              {}

            if (!emittedToolCalls.has(toolCallId)) {
              emittedToolCalls.add(toolCallId)
              enqueueEvent(controller, {
                type: "tool-input-start",
                toolCallId,
                toolName,
              })
              enqueueEvent(controller, {
                type: "tool-input-available",
                toolCallId,
                toolName,
                input,
              })
            }
          }
        }
      } else if (type === "tool") {
        const toolCallId = String(
          (message as { tool_call_id?: unknown }).tool_call_id ?? ""
        )
        const output =
          contentToString((message as { content: unknown }).content) ?? ""
        if (toolCallId && !emittedToolOutputs.has(toolCallId)) {
          emittedToolOutputs.add(toolCallId)
          enqueueEvent(controller, {
            type: "tool-output-available",
            toolCallId,
            output,
          })
        }
      }
    }
  }

  function processLangGraphEvent(
    controller: TransformStreamDefaultController<Uint8Array>,
    data: string
  ) {
    let parsed: unknown
    try {
      parsed = JSON.parse(data)
    } catch {
      return
    }

    if (!parsed || typeof parsed !== "object") return

    const event = parsed as {
      event?: string
      name?: string
      data?: unknown
    }

    if (event.event === "on_custom_event" && event.name === "agent_update") {
      const payload = event.data
      if (payload && typeof payload === "object") {
        enqueueEvent(controller, {
          type: "data-agent",
          id: crypto.randomUUID().slice(0, 8),
          data: payload,
        })
      }
    }
  }

  let currentEvent = ""
  let pendingData = ""

  function flushPendingEvent(
    controller: TransformStreamDefaultController<Uint8Array>
  ) {
    if (!currentEvent || !pendingData) return

    if (
      currentEvent === "messages/partial" ||
      currentEvent === "messages/complete" ||
      currentEvent === "messages"
    ) {
      processMessagesEvent(controller, pendingData)
    } else if (currentEvent === "events") {
      processLangGraphEvent(controller, pendingData)
    } else if (currentEvent === "error") {
      let parsed: { error?: string; message?: string } = {}
      try {
        parsed = JSON.parse(pendingData) as { error?: string; message?: string }
      } catch {
        parsed = {}
      }
      const errorText = `${parsed.error || "Backend error"}: ${parsed.message || "run failed"}`
      enqueueEvent(controller, { type: "error", errorText })
      errored = true
    }

    pendingData = ""
  }

  function processLine(
    line: string,
    controller: TransformStreamDefaultController<Uint8Array>
  ) {
    const trimmed = line.trim()
    if (!trimmed) return

    if (trimmed.startsWith("event:")) {
      flushPendingEvent(controller)
      currentEvent = trimmed.slice(6).trim()
    } else if (trimmed.startsWith("data:")) {
      const value = trimmed.slice(5).trim()
      pendingData = pendingData ? `${pendingData}\n${value}` : value
    }
  }

  return new TransformStream<Uint8Array, Uint8Array>({
    start(controller) {
      enqueueEvent(controller, { type: "start", messageId })
    },

    transform(chunk, controller) {
      buffer += decoder.decode(chunk, { stream: true })

      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""

      for (const line of lines) {
        processLine(line, controller)
      }
    },

    flush(controller) {
      if (buffer.trim()) {
        processLine(buffer.trim(), controller)
      }

      flushPendingEvent(controller)

      if (textStarted) {
        enqueueEvent(controller, { type: "text-end", id: textBlockId })
      }
      enqueueEvent(controller, { type: "finish" })
      enqueueEvent(controller, "[DONE]")
    },
  })
}

const CLIENT_TEAM_SYSTEM_NOTE =
  "The current user belongs to the Client Team (read-only access). " +
  "Do NOT call run_pentest, run_osint, run_research or any other scanning/" +
  "report-generation tool. If the user asks to scan the system or generate a " +
  "report, politely explain (in the user's language) that running scans " +
  "requires the Admin or Enterprise Team, and offer to discuss the existing " +
  "reports instead."

export async function action({ request }: ActionFunctionArgs) {
  const body = (await request.json()) as {
    messages?: UIMessage[]
    id?: string
    threadId?: string
    team?: string
  }
  const messages = body.messages ?? []
  const locale = getLocaleFromRequest(request)

  if (messages.length === 0) {
    return createDataStream(translate(locale, "error.noMessages"))
  }

  const threadId = body.id ?? body.threadId ?? crypto.randomUUID()
  const title = buildChatTitle(messages, locale)
  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const threadResponse = await fetch(`${backendUrl}/threads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: threadId,
        assistant_id: "frontdesk",
        if_exists: "do_nothing",
        metadata: { graph_id: "frontdesk", title },
      }),
    })

    if (!threadResponse.ok) {
      const text = await threadResponse.text()
      return createDataStream(
        translate(locale, "error.threadCreate", {
          status: threadResponse.status,
          detail: text.slice(0, 500),
        })
      )
    }

    const langGraphMessages = messages.map((message) => ({
      role: message.role === "user" ? "user" : "assistant",
      content: extractTextFromUIMessage(message),
    }))

    if (body.team === "client") {
      langGraphMessages.unshift({
        role: "system",
        content: CLIENT_TEAM_SYSTEM_NOTE,
      })
    }

    const backendResponse = await fetch(
      `${backendUrl}/threads/${threadId}/runs/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          assistant_id: "frontdesk",
          input: { messages: langGraphMessages },
          stream_mode: ["messages", "events"],
        }),
      }
    )

    if (!backendResponse.ok) {
      const text = await backendResponse.text()
      return createDataStream(
        translate(locale, "error.backend", {
          status: backendResponse.status,
          detail: text.slice(0, 500),
        })
      )
    }

    if (!backendResponse.body) {
      return createDataStream(translate(locale, "error.noBody"))
    }

    const stream = backendResponse.body.pipeThrough(
      createLangGraphStreamTransformer()
    )

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "x-vercel-ai-ui-message-stream": "v1",
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return createDataStream(
      translate(locale, "error.connect", { url: backendUrl, message })
    )
  }
}
