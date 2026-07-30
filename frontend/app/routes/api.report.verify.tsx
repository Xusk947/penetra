import type { ActionFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

export async function action({ request, params }: ActionFunctionArgs) {
  const reportId = params.reportId
  if (!reportId) {
    return Response.json({ error: "No report id" }, { status: 400 })
  }

  if (request.method !== "POST") {
    return Response.json({ error: "Method not allowed" }, { status: 405 })
  }

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(`${backendUrl}/reports/${reportId}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
    })
    if (!response.ok) {
      const text = await response.text()
      return Response.json({ error: text }, { status: response.status })
    }
    const data = await response.json()
    return Response.json(data)
  } catch {
    return Response.json({ error: "Failed to verify" }, { status: 500 })
  }
}
