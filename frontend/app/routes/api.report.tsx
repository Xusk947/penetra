import type { ActionFunctionArgs, LoaderFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

export async function action({ request, params }: ActionFunctionArgs) {
  const reportId = params.reportId
  if (!reportId) {
    return Response.json({ error: "No report id" }, { status: 400 })
  }

  if (request.method !== "DELETE" && request.method !== "PATCH") {
    return Response.json({ error: "Method not allowed" }, { status: 405 })
  }

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(`${backendUrl}/reports/${reportId}`, {
      method: request.method,
      headers:
        request.method === "PATCH"
          ? { "Content-Type": "application/json" }
          : undefined,
      body: request.method === "PATCH" ? await request.text() : undefined,
    })
    if (!response.ok) {
      const text = await response.text()
      return Response.json({ error: text }, { status: response.status })
    }
    if (request.method === "DELETE") {
      return Response.json({ deleted: reportId })
    }
    const data = await response.json()
    return Response.json(data)
  } catch {
    return Response.json({ error: "Failed to update" }, { status: 500 })
  }
}

export async function loader({ params }: LoaderFunctionArgs) {
  const reportId = params.reportId
  if (!reportId) {
    return Response.json({ report: null })
  }

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(`${backendUrl}/reports/${reportId}`)
    if (!response.ok) {
      return Response.json({ report: null })
    }
    const data = await response.json()
    return Response.json({ report: data })
  } catch {
    return Response.json({ report: null })
  }
}
