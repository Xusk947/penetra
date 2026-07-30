import type { UIMessage } from "ai"
import type { LoaderFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

function contentToString(content: unknown): string {
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
  return String(content ?? "")
}

interface LangGraphToolCall {
  id?: string
  name?: string
  args?: Record<string, unknown>
  input?: Record<string, unknown>
}

interface ToolResult {
  content: string
  name?: string
}

function buildToolResultMap(messages: unknown[]) {
  const map = new Map<string, ToolResult>()

  for (const message of messages) {
    if (!message || typeof message !== "object") continue
    const type =
      (message as { type?: unknown }).type ??
      (message as { role?: unknown }).role
    if (type !== "tool") continue

    const toolCallId = String(
      (message as { tool_call_id?: unknown }).tool_call_id ?? ""
    )
    if (!toolCallId) continue

    const name = String((message as { name?: unknown }).name ?? "")
    const content = contentToString((message as { content: unknown }).content)
    map.set(toolCallId, { content, name })
  }

  return map
}

function langGraphMessageToUIMessage(
  message: unknown,
  toolResults: Map<string, ToolResult>
): UIMessage | null {
  if (!message || typeof message !== "object") return null

  const role =
    (message as { type?: unknown }).type ?? (message as { role?: unknown }).role

  if (role === "human" || role === "user") {
    const id = (message as { id?: string }).id ?? crypto.randomUUID()
    const text = contentToString((message as { content: unknown }).content)
    return { id, role: "user", parts: [{ type: "text" as const, text }] }
  }

  if (role === "ai" || role === "assistant") {
    const id = (message as { id?: string }).id ?? crypto.randomUUID()
    const parts: UIMessage["parts"] = []

    const text = contentToString((message as { content: unknown }).content)
    if (text) {
      parts.push({ type: "text" as const, text })
    }

    const toolCalls = (message as { tool_calls?: unknown }).tool_calls
    if (Array.isArray(toolCalls)) {
      for (const toolCall of toolCalls) {
        if (!toolCall || typeof toolCall !== "object") continue
        const call = toolCall as LangGraphToolCall
        const toolCallId = String(call.id ?? crypto.randomUUID())
        const toolName =
          call.name ?? (call as { toolName?: string }).toolName ?? "tool"
        const input = call.args ?? call.input ?? {}
        const result = toolResults.get(toolCallId)

        const part: Record<string, unknown> = {
          type: `tool-${toolName}`,
          toolCallId,
          toolName,
          state: result ? "output-available" : "input-available",
          input,
        }

        if (result) {
          part.output = result.content
        }

        parts.push(part as UIMessage["parts"][number])
      }
    }

    return { id, role: "assistant", parts }
  }

  return null
}

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url)
  const threadId = url.searchParams.get("threadId")

  if (!threadId) {
    return Response.json({ messages: [] })
  }

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(`${backendUrl}/threads/${threadId}`, {
      headers: { Accept: "application/json" },
    })

    if (!response.ok) {
      return Response.json({ messages: [] })
    }

    const thread = (await response.json()) as {
      metadata?: { title?: string } | null
      values?: { messages?: unknown[] }
    }

    const title = thread.metadata?.title ?? null
    const langGraphMessages = thread.values?.messages ?? []
    const toolResults = buildToolResultMap(langGraphMessages)
    const messages: UIMessage[] = []

    for (const message of langGraphMessages) {
      const uiMessage = langGraphMessageToUIMessage(message, toolResults)
      if (uiMessage) messages.push(uiMessage)
    }

    return Response.json({ messages, title })
  } catch {
    return Response.json({ messages: [] })
  }
}
