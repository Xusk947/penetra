"use client"

import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  Cancel01Icon,
  Chat01Icon,
  CheckmarkBadge01Icon,
  Delete01Icon,
  File01Icon,
  Menu01Icon,
} from "@hugeicons/core-free-icons"

import { ConfirmDialog } from "~/components/confirm-dialog"
import { TeamSelect } from "~/components/team-select"
import { Button } from "~/components/ui/button"
import { ScrollArea } from "~/components/ui/scroll-area"
import { Skeleton } from "~/components/ui/skeleton"
import { useTeam } from "~/lib/team"
import { cn } from "~/lib/utils"

interface ChatThread {
  id: string
  title: string
  updatedAt: string
}

interface ReportItem {
  id: string
  title: string
  created_at: string
  findings_count: number
  verified?: boolean
}

interface DeleteTarget {
  type: "thread" | "report"
  id: string
  title: string
}

function useActiveRoute() {
  const location = useLocation()
  const path = location.pathname

  const chatMatch = path.match(/^\/chat(?:\/([^/]+))?$/)
  const reportsMatch = path.match(/^\/reports(?:\/([^/]+))?$/)

  return {
    tab: reportsMatch ? "reports" : "chat",
    threadId: chatMatch ? (chatMatch[1] ?? null) : null,
    reportId: reportsMatch ? (reportsMatch[1] ?? null) : null,
    path,
  }
}

function SidebarSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-2 p-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex flex-col gap-1.5 rounded-lg p-2">
          <Skeleton className="h-3.5 w-3/4" />
          <Skeleton className="h-2.5 w-1/2" />
        </div>
      ))}
    </div>
  )
}

export function Sidebar({
  isOpen,
  onToggle,
}: {
  isOpen: boolean
  onToggle: () => void
}) {
  const navigate = useNavigate()
  const { team } = useTeam()
  const { tab, threadId, reportId, path } = useActiveRoute()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [loadingReports, setLoadingReports] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)

  useEffect(() => {
    if (tab !== "chat") return
    setLoadingThreads(true)
    fetch("/api/chat/threads")
      .then((res) => res.json())
      .then((data: { threads?: ChatThread[] }) => {
        setThreads(data.threads ?? [])
      })
      .catch(() => setThreads([]))
      .finally(() => setLoadingThreads(false))
  }, [tab, path])

  useEffect(() => {
    if (tab !== "reports") return
    setLoadingReports(true)
    fetch("/api/reports")
      .then((res) => res.json())
      .then((data: { reports?: ReportItem[] }) => {
        setReports(data.reports ?? [])
      })
      .catch(() => setReports([]))
      .finally(() => setLoadingReports(false))
  }, [tab, path])

  const handleNewChat = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("threadId")
    }
    navigate("/chat", { replace: true })
  }

  const handleSelectThread = (id: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("threadId", id)
    }
    navigate(`/chat/${id}`, { replace: true })
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      onToggle()
    }
  }

  const handleSelectReport = (id: string) => {
    navigate(`/reports/${id}`, { replace: true })
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      onToggle()
    }
  }

  const handleDeleteThread = async (id: string) => {
    try {
      const response = await fetch(`/api/chat/threads/${id}`, {
        method: "DELETE",
      })
      if (response.ok) {
        setThreads((prev) => prev.filter((thread) => thread.id !== id))
        if (threadId === id) {
          navigate("/chat", { replace: true })
        }
      }
    } catch {
      // ignore
    }
  }

  const handleDeleteReport = async (id: string) => {
    try {
      const response = await fetch(`/api/reports/${id}`, {
        method: "DELETE",
      })
      if (response.ok) {
        setReports((prev) => prev.filter((report) => report.id !== id))
        if (reportId === id) {
          navigate("/reports", { replace: true })
        }
      }
    } catch {
      // ignore
    }
  }

  const confirmDelete = () => {
    if (!deleteTarget) return
    if (deleteTarget.type === "thread") {
      handleDeleteThread(deleteTarget.id)
    } else {
      handleDeleteReport(deleteTarget.id)
    }
    setDeleteTarget(null)
  }

  const sortedThreads = [...threads].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  )

  const sortedReports = [...reports].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  if (!isOpen) {
    return (
      <aside className="hidden h-svh w-14 flex-col items-center border-r border-border bg-card pt-3 lg:flex">
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center justify-center rounded-md p-2 text-foreground hover:bg-muted"
          aria-label="Открыть боковую панель"
        >
          <HugeiconsIcon icon={Menu01Icon} className="size-5" />
        </button>
      </aside>
    )
  }

  return (
    <aside className="fixed left-0 top-0 z-50 flex h-svh w-64 flex-col bg-card lg:static">
      <div className="px-3 pt-3 pb-1">
        <div className="flex items-center justify-between">
          <div className="font-heading text-base font-semibold tracking-tight">
            Penetra
          </div>
          <button
            type="button"
            onClick={onToggle}
            className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Свернуть боковую панель"
          >
            <HugeiconsIcon icon={Cancel01Icon} className="size-4" />
          </button>
        </div>
      </div>
      <div className="px-2 pb-1">
        <TeamSelect />
      </div>
      <div className="p-2">
        <div className="flex gap-1 rounded-lg bg-muted/50 p-1">
          <button
            type="button"
            onClick={() => navigate("/chat")}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
              tab === "chat"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <HugeiconsIcon icon={Chat01Icon} className="size-3.5" />
            Чат
          </button>
          <button
            type="button"
            onClick={() => navigate("/reports")}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
              tab === "reports"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <HugeiconsIcon icon={File01Icon} className="size-3.5" />
            Репорты
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={deleteTarget !== null}
        title="Подтвердите удаление"
        message={
          deleteTarget
            ? `Точно удалить «${deleteTarget.title}»? Действие необратимо.`
            : ""
        }
        confirmText="Удалить"
        cancelText="Отмена"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {tab === "chat" && (
        <>
          <div className="px-2 pb-2">
            <Button
              variant="secondary"
              className="w-full"
              onPress={handleNewChat}
            >
              Новый чат
            </Button>
          </div>
          <ScrollArea className="flex-1">
            <div className="flex flex-col gap-1 p-2">
              {sortedThreads.map((thread) => {
                const isActive = thread.id === threadId
                return (
                  <div
                    key={thread.id}
                    className={cn(
                      "group relative flex w-full items-center rounded-lg transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => handleSelectThread(thread.id)}
                      className="flex flex-1 flex-col px-2 py-1.5 text-left text-xs"
                      title={thread.title}
                    >
                      <div className="truncate font-medium">{thread.title}</div>
                      <div
                        className={cn(
                          "truncate text-[10px] opacity-60",
                          isActive && "text-primary-foreground"
                        )}
                      >
                        {new Date(thread.updatedAt).toLocaleString("ru-RU", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </button>
                    {team.canDelete && (
                      <button
                        type="button"
                        onClick={() =>
                          setDeleteTarget({
                            type: "thread",
                            id: thread.id,
                            title: thread.title,
                          })
                        }
                        className={cn(
                          "flex items-center justify-center p-2 opacity-70 transition-opacity lg:opacity-0 lg:group-hover:opacity-100",
                          isActive
                            ? "text-primary-foreground hover:text-white"
                            : "text-muted-foreground hover:text-destructive"
                        )}
                        aria-label="Удалить чат"
                        title="Удалить чат"
                      >
                        <HugeiconsIcon
                          icon={Delete01Icon}
                          className="size-3.5"
                        />
                      </button>
                    )}
                  </div>
                )
              })}

              {loadingThreads && threads.length === 0 && <SidebarSkeleton />}

              {threads.length === 0 && !loadingThreads && (
                <div className="px-2 py-4 text-center text-xs text-muted-foreground">
                  Нет чатов
                </div>
              )}
            </div>
          </ScrollArea>
        </>
      )}

      {tab === "reports" && (
        <ScrollArea className="flex-1">
          <div className="flex flex-col gap-1 p-2">
            {sortedReports.map((report) => {
              const isActive = report.id === reportId
              return (
                <div
                  key={report.id}
                  className={cn(
                    "group relative flex w-full items-center rounded-lg transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted"
                  )}
                >
                  <button
                    type="button"
                    onClick={() => handleSelectReport(report.id)}
                    className="flex flex-1 flex-col px-2 py-1.5 text-left text-xs"
                    title={report.title}
                  >
                    <div className="flex items-center gap-1 truncate font-medium">
                      <span className="truncate">{report.title}</span>
                      {report.verified && (
                        <HugeiconsIcon
                          icon={CheckmarkBadge01Icon}
                          className={cn(
                            "size-3 shrink-0",
                            isActive ? "text-primary-foreground" : "text-primary"
                          )}
                        />
                      )}
                    </div>
                    <div
                      className={cn(
                        "truncate text-[10px] opacity-60",
                        isActive && "text-primary-foreground"
                      )}
                    >
                      {new Date(report.created_at).toLocaleString("ru-RU", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      {report.findings_count > 0
                        ? ` · ${report.findings_count} находок`
                        : ""}
                    </div>
                  </button>
                  {team.canDelete && (
                    <button
                      type="button"
                      onClick={() =>
                        setDeleteTarget({
                          type: "report",
                          id: report.id,
                          title: report.title,
                        })
                      }
                      className={cn(
                        "flex items-center justify-center p-2 opacity-70 transition-opacity lg:opacity-0 lg:group-hover:opacity-100",
                        isActive
                          ? "text-primary-foreground hover:text-white"
                          : "text-muted-foreground hover:text-destructive"
                      )}
                      aria-label="Удалить репорт"
                      title="Удалить репорт"
                    >
                      <HugeiconsIcon icon={Delete01Icon} className="size-3.5" />
                    </button>
                  )}
                </div>
              )
            })}

            {loadingReports && reports.length === 0 && <SidebarSkeleton />}

            {reports.length === 0 && !loadingReports && (
              <div className="px-2 py-4 text-center text-xs text-muted-foreground">
                Нет репортов
              </div>
            )}
          </div>
        </ScrollArea>
      )}
    </aside>
  )
}
