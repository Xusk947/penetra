import type { LoaderFunctionArgs } from "react-router"

import { getLocaleFromRequest, translate } from "~/lib/i18n"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

interface ThreadItem {
  thread_id: string
  updated_at: string
  metadata?: { title?: string } | null
}

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url)
  const limit = url.searchParams.get("limit") ?? "100"
  const offset = url.searchParams.get("offset") ?? "0"

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL
  const locale = getLocaleFromRequest(request)

  try {
    const response = await fetch(`${backendUrl}/threads/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: Number(limit),
        offset: Number(offset),
      }),
    })

    if (!response.ok) {
      return Response.json({ threads: [] })
    }

    const items = (await response.json()) as ThreadItem[]

    const threads = items.map((item) => ({
      id: item.thread_id,
      title:
        item.metadata?.title?.trim() ||
        translate(locale, "chat.threadFallback", {
          id: item.thread_id.slice(0, 8),
        }),
      updatedAt: item.updated_at,
    }))

    return Response.json({ threads })
  } catch {
    return Response.json({ threads: [] })
  }
}
