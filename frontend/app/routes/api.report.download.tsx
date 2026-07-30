import type { LoaderFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

export async function loader({ request, params }: LoaderFunctionArgs) {
  const reportId = params.reportId
  if (!reportId) {
    return new Response("Not found", { status: 404 })
  }

  const url = new URL(request.url)
  const format = url.searchParams.get("format") || "md"

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(
      `${backendUrl}/reports/${reportId}/download?format=${format}`
    )
    if (!response.ok) {
      return new Response("Failed to fetch", { status: response.status })
    }

    const headers = new Headers()
    headers.set(
      "Content-Type",
      response.headers.get("content-type") || "application/octet-stream"
    )
    const contentDisposition = response.headers.get("content-disposition")
    if (contentDisposition) {
      headers.set("Content-Disposition", contentDisposition)
    } else {
      headers.set(
        "Content-Disposition",
        `attachment; filename="report_${reportId}.${format}"`
      )
    }

    return new Response(response.body, { headers })
  } catch {
    return new Response("Failed to fetch", { status: 500 })
  }
}
