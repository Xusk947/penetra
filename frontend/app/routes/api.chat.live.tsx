import type { LoaderFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url)
  const threadId = url.searchParams.get("threadId")

  if (!threadId) {
    return new Response("Missing threadId", { status: 400 })
  }

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(
      `${backendUrl}/threads/${encodeURIComponent(threadId)}/live`,
      {
        headers: {
          Accept: "text/event-stream",
        },
      }
    )

    if (!response.ok) {
      const text = await response.text()
      return new Response(`Backend error: ${text.slice(0, 500)}`, {
        status: 502,
      })
    }

    if (!response.body) {
      return new Response("No response body", { status: 502 })
    }

    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return new Response(`Failed to connect to backend: ${message}`, {
      status: 502,
    })
  }
}
