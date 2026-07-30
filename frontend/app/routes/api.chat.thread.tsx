import type { ActionFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

export async function action({ request, params }: ActionFunctionArgs) {
  const threadId = params.threadId
  if (!threadId) {
    return Response.json({ error: "No thread id" }, { status: 400 })
  }

  if (request.method !== "DELETE") {
    return Response.json({ error: "Method not allowed" }, { status: 405 })
  }

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(`${backendUrl}/threads/${threadId}`, {
      method: "DELETE",
    })
    if (!response.ok) {
      const text = await response.text()
      return Response.json({ error: text }, { status: response.status })
    }
    return Response.json({ deleted: threadId })
  } catch {
    return Response.json({ error: "Failed to delete" }, { status: 500 })
  }
}
