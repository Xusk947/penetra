import {
  type RouteConfig,
  index,
  route,
  layout,
} from "@react-router/dev/routes"

export default [
  layout("routes/_layout.tsx", [
    index("routes/home.tsx"),
    route("chat/:threadId?", "routes/home.tsx", { id: "chat" }),
    route("reports/:reportId?", "routes/report.tsx"),
  ]),

  route("api/chat", "routes/api.chat.tsx"),
  route("api/chat/history", "routes/api.chat.history.tsx"),
  route("api/chat/threads", "routes/api.chat.threads.tsx"),
  route("api/chat/threads/:threadId", "routes/api.chat.thread.tsx"),
  route("api/reports", "routes/api.reports.tsx"),
  route("api/reports/:reportId/download", "routes/api.report.download.tsx"),
  route("api/reports/:reportId/verify", "routes/api.report.verify.tsx"),
  route("api/reports/:reportId", "routes/api.report.tsx"),
] satisfies RouteConfig
