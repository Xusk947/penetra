import type { UIMessage } from "ai"
import type { LoaderFunctionArgs } from "react-router"

import {
  buildToolResultMap,
  langGraphMessageToUIMessage,
} from "~/lib/messages"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

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
