import type { LoaderFunctionArgs } from "react-router"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url)
  const limit = url.searchParams.get("limit") ?? "100"
  const offset = url.searchParams.get("offset") ?? "0"

  const backendUrl = process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL

  try {
    const response = await fetch(
      `${backendUrl}/reports?limit=${limit}&offset=${offset}`
    )
    if (!response.ok) {
      return Response.json({ reports: [] })
    }
    const data = (await response.json()) as { reports: unknown[] }
    return Response.json(data)
  } catch {
    return Response.json({ reports: [] })
  }
}
