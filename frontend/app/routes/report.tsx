"use client"

import { useState } from "react"
import {
  useLoaderData,
  useParams,
  useRevalidator,
  type LoaderFunctionArgs,
} from "react-router"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowDown01Icon,
  CheckIcon,
  CheckmarkBadge01Icon,
  Copy01Icon,
  Download01Icon,
  Loading01Icon,
  PencilEdit01Icon,
} from "@hugeicons/core-free-icons"

import { Markdown } from "~/components/markdown"
import {
  ReportEditor,
  type EditableFinding,
} from "~/components/report-editor"
import { ScrollArea } from "~/components/ui/scroll-area"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "~/components/ui/card"
import { useI18n, type TranslateFn } from "~/lib/i18n"
import { useTeam } from "~/lib/team"
import { cn } from "~/lib/utils"

const DEFAULT_BACKEND_URL = "http://127.0.0.1:2024"

interface Finding {
  id: string
  title: string
  findingId?: string
  agent?: string
  tool?: string
  category?: string
  severity: string
  score?: string
  confidence?: string
  cwe?: string
  description: string
  trace: string[]
  remediation?: string
}

interface BackendFinding {
  id?: string
  title: string
  severity: string
  confidence?: string
  description: string
  cwe?: string | null
  remediation?: string | null
  category?: string | null
  score?: number | null
  steps?: string[]
  agent?: string | null
  tool?: string | null
}

interface ReportData {
  id: string
  title: string
  scope: string[]
  findings_count: number
  markdown: string
  verified?: boolean
  verified_at?: string | null
  findings?: BackendFinding[] | null
}

function backendFindingToUi(finding: BackendFinding): Finding {
  return {
    id: finding.id ?? crypto.randomUUID(),
    title: finding.title,
    findingId: finding.id,
    agent: finding.agent ?? undefined,
    tool: finding.tool ?? undefined,
    category: finding.category ?? undefined,
    severity: finding.severity || "info",
    score: finding.score != null ? `${finding.score}/5` : undefined,
    confidence: finding.confidence,
    cwe: finding.cwe ?? undefined,
    description: finding.description,
    trace: finding.steps ?? [],
    remediation: finding.remediation ?? undefined,
  }
}

function backendFindingToEditable(finding: BackendFinding): EditableFinding {
  return {
    id: finding.id ?? crypto.randomUUID(),
    title: finding.title,
    severity: finding.severity || "info",
    confidence: finding.confidence || "certain",
    description: finding.description,
    cwe: finding.cwe ?? "",
    remediation: finding.remediation ?? "",
    category: finding.category ?? "general",
    score: finding.score ?? null,
    steps: finding.steps ?? [],
    agent: finding.agent ?? "",
    tool: finding.tool ?? "",
  }
}

function parseFindingBlock(block: string, id: string, title: string): Finding {
  const lines = block.split("\n")
  let i = 0

  while (i < lines.length && !lines[i].trim().startsWith("###")) i++
  if (i < lines.length && lines[i].trim().startsWith("###")) i++

  const metadata: Record<string, string> = {}
  while (i < lines.length) {
    const trimmed = lines[i].trim()
    if (
      trimmed.startsWith("**") &&
      /^\*\*(Description|Trace|Remediation)/.test(trimmed)
    ) {
      break
    }
    const match = trimmed.match(/^-\s+\*\*([^*]+?)\*\*:\s*(.*)$/)
    if (match) {
      metadata[match[1].trim()] = match[2].trim()
    }
    i++
  }

  let description = ""
  if (i < lines.length && lines[i].trim().startsWith("**Description:**")) {
    const label = "**Description:**"
    const line = lines[i].trim()
    const contentStart = line.indexOf(label) + label.length
    const parts: string[] = []
    if (contentStart < line.length) {
      parts.push(line.slice(contentStart).trim())
    }
    i++
    while (i < lines.length) {
      const trimmed = lines[i].trim()
      if (
        trimmed.startsWith("**") &&
        /^\*\*(Trace|Remediation)/.test(trimmed)
      ) {
        break
      }
      if (trimmed !== "") parts.push(trimmed)
      i++
    }
    description = parts.join("\n").trim()
  }

  const trace: string[] = []
  if (
    i < lines.length &&
    lines[i].trim().startsWith("**Trace (steps taken):**")
  ) {
    i++
    while (i < lines.length) {
      const trimmed = lines[i].trim()
      if (trimmed.startsWith("**") && trimmed.startsWith("**Remediation")) {
        break
      }
      if (trimmed === "") {
        i++
        continue
      }
      const step = trimmed.replace(/^\d+\.\s*/, "")
      trace.push(step)
      i++
    }
  }

  let remediation = ""
  if (i < lines.length && lines[i].trim().startsWith("**Remediation:**")) {
    const label = "**Remediation:**"
    const line = lines[i].trim()
    const contentStart = line.indexOf(label) + label.length
    const parts: string[] = []
    if (contentStart < line.length) {
      parts.push(line.slice(contentStart).trim())
    }
    i++
    while (i < lines.length) {
      const trimmed = lines[i].trim()
      if (trimmed.startsWith("###")) break
      if (trimmed !== "") parts.push(trimmed)
      i++
    }
    remediation = parts.join("\n").trim()
  }

  return {
    id,
    title,
    findingId: metadata["Finding ID"],
    agent: metadata["Agent"],
    tool: metadata["Tool/check"],
    category: metadata["Category"],
    severity: metadata["Severity"] || "info",
    score: metadata["Score"],
    confidence: metadata["Confidence"],
    cwe: metadata["CWE"],
    description,
    trace,
    remediation,
  }
}

function parseReport(markdown: string): Finding[] {
  const findings: Finding[] = []
  const headingRegex = /^###\s+\d+\.\s+\[([A-Z0-9-]+)\]\s+(.+)$/gm
  const matches: { index: number; id: string; title: string }[] = []
  let match: RegExpExecArray | null
  while ((match = headingRegex.exec(markdown)) !== null) {
    matches.push({ index: match.index, id: match[1], title: match[2].trim() })
  }

  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].index
    const end = i < matches.length - 1 ? matches[i + 1].index : markdown.length
    const block = markdown.slice(start, end)
    findings.push(parseFindingBlock(block, matches[i].id, matches[i].title))
  }

  return findings
}

const SEVERITY_CLASS: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-amber-500 text-black",
  low: "bg-blue-500 text-white",
  info: "bg-muted text-muted-foreground",
}

function getSeverity(severity: string, t: TranslateFn) {
  const key = severity.toLowerCase()
  if (key in SEVERITY_CLASS) {
    return {
      label: t(`severity.${key}`),
      className: SEVERITY_CLASS[key],
      description: t(`severity.${key}.desc`),
    }
  }
  return {
    label: severity,
    className: "bg-muted text-muted-foreground",
    description: t("severity.unknown.desc"),
  }
}

function FieldBadge({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <span className="inline-flex items-center rounded-md bg-muted/50 px-1.5 py-0.5 text-[10px]">
      <span className="text-muted-foreground">{label}:</span>
      <span className="ml-0.5 font-medium">{value}</span>
    </span>
  )
}

function SimpleTooltip({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <span className="group relative inline-flex cursor-help">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden w-48 -translate-x-1/2 rounded-md bg-foreground px-2 py-1 text-left text-[10px] text-background shadow-lg group-hover:block">
        {label}
      </span>
    </span>
  )
}

function formatFinding(finding: Finding, t: TranslateFn): string {
  const lines: string[] = []
  lines.push(`${finding.findingId ?? finding.id}: ${finding.title}`)
  const severity = getSeverity(finding.severity, t)
  lines.push(`${t("field.severity")}: ${severity.label}`)
  if (finding.score) lines.push(`${t("field.score")}: ${finding.score}`)
  if (finding.agent) lines.push(`${t("field.agent")}: ${finding.agent}`)
  if (finding.tool) lines.push(`${t("field.tool")}: ${finding.tool}`)
  if (finding.category) lines.push(`${t("field.category")}: ${finding.category}`)
  if (finding.confidence)
    lines.push(`${t("field.confidence")}: ${finding.confidence}`)
  if (finding.cwe) lines.push(`${t("field.cwe")}: ${finding.cwe}`)
  lines.push("")
  lines.push(`${t("section.description")}:`)
  lines.push(finding.description)
  if (finding.trace.length > 0) {
    lines.push("")
    lines.push(`${t("section.steps")}:`)
    finding.trace.forEach((step, idx) => {
      lines.push(`${idx + 1}. ${step}`)
    })
  }
  if (finding.remediation) {
    lines.push("")
    lines.push(`${t("section.remediation")}:`)
    lines.push(finding.remediation)
  }
  return lines.join("\n")
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
    const report = (await response.json()) as ReportData
    return Response.json({ report })
  } catch {
    return Response.json({ report: null })
  }
}

export default function Report() {
  const params = useParams()
  const { report } = useLoaderData() as { report: ReportData | null }
  const { team } = useTeam()
  const { t, dateTag } = useI18n()
  const revalidator = useRevalidator()
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [copied, setCopied] = useState<Record<string, boolean>>({})
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  if (!params.reportId) {
    return (
      <div className="relative flex h-full w-full max-w-3xl flex-col items-center justify-center rounded-[1.75rem] bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">
          {t("report.selectPrompt")}
        </p>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="relative flex h-full w-full max-w-3xl flex-col items-center justify-center rounded-[1.75rem] bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">{t("report.notFound")}</p>
      </div>
    )
  }

  const findings =
    report.findings && report.findings.length > 0
      ? report.findings.map(backendFindingToUi)
      : parseReport(report.markdown)

  const editableFindings: EditableFinding[] =
    report.findings && report.findings.length > 0
      ? report.findings.map(backendFindingToEditable)
      : parseReport(report.markdown).map((finding) => ({
          id: finding.findingId ?? finding.id,
          title: finding.title,
          severity: finding.severity,
          confidence: finding.confidence ?? "certain",
          description: finding.description,
          cwe: finding.cwe ?? "",
          remediation: finding.remediation ?? "",
          category: finding.category ?? "general",
          score: finding.score ? Number(finding.score.split("/")[0]) : null,
          steps: finding.trace,
          agent: finding.agent ?? "",
          tool: finding.tool ?? "",
        }))

  const saveFindings = async (updated: EditableFinding[]) => {
    setSaving(true)
    setActionError(null)
    try {
      const response = await fetch(`/api/reports/${report.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          findings: updated.map((finding) => ({
            id: finding.id,
            title: finding.title,
            severity: finding.severity,
            confidence: finding.confidence,
            description: finding.description,
            cwe: finding.cwe || null,
            remediation: finding.remediation || null,
            category: finding.category || null,
            score: finding.score,
            steps: finding.steps,
            agent: finding.agent || null,
            tool: finding.tool || null,
          })),
        }),
      })
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as {
          error?: string
          detail?: string
        } | null
        throw new Error(data?.detail ?? data?.error ?? `HTTP ${response.status}`)
      }
      setEditing(false)
      revalidator.revalidate()
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : t("report.saveError")
      )
    } finally {
      setSaving(false)
    }
  }

  const toggleVerified = async () => {
    setVerifying(true)
    setActionError(null)
    try {
      const response = await fetch(`/api/reports/${report.id}/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verified: !report.verified }),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      revalidator.revalidate()
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : t("report.verifyError")
      )
    } finally {
      setVerifying(false)
    }
  }

  const toggleFinding = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const copyFinding = async (finding: Finding) => {
    try {
      await navigator.clipboard.writeText(formatFinding(finding, t))
      setCopied((prev) => ({ ...prev, [finding.id]: true }))
      setTimeout(() => {
        setCopied((prev) => ({ ...prev, [finding.id]: false }))
      }, 2000)
    } catch {
      // ignore
    }
  }

  const exportPdf = () => {
    window.open(`/api/reports/${report.id}/download?format=pdf`, "_blank")
  }

  return (
    <div className="relative flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-[1.75rem] bg-card">
      <div className="flex flex-col gap-2 border-b p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:gap-2">
          <div className="truncate font-heading text-sm font-medium">
            {report.title}
          </div>
          {report.verified && (
            <span
              className="flex shrink-0 items-center gap-1 rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary"
              title={
                report.verified_at
                  ? t("report.verifiedTooltipAt", {
                      date: new Date(report.verified_at).toLocaleString(dateTag),
                    })
                  : t("report.verifiedTooltip")
              }
            >
              <HugeiconsIcon
                icon={CheckmarkBadge01Icon}
                className="size-3.5"
              />
              {t("report.verifiedByAdmin")}
            </span>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {team.canVerify && !editing && (
            <button
              type="button"
              onClick={toggleVerified}
              disabled={verifying}
              className={cn(
                "flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors",
                report.verified
                  ? "border-primary bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              title={t("report.verifiedTooltip")}
            >
              <HugeiconsIcon
                icon={verifying ? Loading01Icon : CheckmarkBadge01Icon}
                className={cn("size-3.5", verifying && "animate-spin")}
              />
              {report.verified ? t("report.unverify") : t("report.verify")}
            </button>
          )}
          {team.canEditReports && (
            <button
              type="button"
              onClick={() => setEditing((prev) => !prev)}
              className={cn(
                "flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors",
                editing
                  ? "border-primary bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <HugeiconsIcon icon={PencilEdit01Icon} className="size-3.5" />
              {editing ? t("report.view") : t("report.edit")}
            </button>
          )}
          <button
            type="button"
            onClick={exportPdf}
            className="flex items-center gap-1 rounded-md bg-primary px-2 py-1 text-[10px] font-medium text-primary-foreground hover:bg-primary/80"
          >
            <HugeiconsIcon icon={Download01Icon} className="size-3.5" />
            PDF
          </button>
        </div>
      </div>
      <ScrollArea className="flex-1 p-4 pr-2">
        {editing ? (
          <div className="space-y-2">
            {actionError && (
              <div className="rounded-md bg-destructive/10 p-2 text-xs text-destructive">
                {actionError}
              </div>
            )}
            <ReportEditor
              initialFindings={editableFindings}
              saving={saving}
              onSave={saveFindings}
              onCancel={() => setEditing(false)}
            />
          </div>
        ) : (
        <div className="space-y-4 pb-2">
          <div className="text-xs text-muted-foreground">
            Scope: {report.scope.join(", ")} · Findings: {report.findings_count}
          </div>
          {actionError && (
            <div className="rounded-md bg-destructive/10 p-2 text-xs text-destructive">
              {actionError}
            </div>
          )}

          {findings.map((finding) => {
            const severity = getSeverity(finding.severity, t)
            return (
              <Card
                key={finding.id}
                className="bg-card"
                onClick={(event) => {
                  if (
                    event.target instanceof HTMLElement &&
                    event.target.closest("button, a")
                  ) {
                    return
                  }
                  toggleFinding(finding.id)
                }}
              >
                <CardHeader>
                  <div className="flex flex-col items-start justify-between gap-2 sm:flex-row">
                    <div className="min-w-0 flex-1">
                      <CardTitle className="text-sm leading-tight font-medium">
                        {finding.title}
                      </CardTitle>
                      <CardDescription className="text-[10px]">
                        {finding.findingId ?? finding.id}
                      </CardDescription>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-1">
                      <SimpleTooltip label={severity.description}>
                        <span
                          className={cn(
                            "rounded-md px-1.5 py-0.5 text-[10px] font-medium uppercase",
                            severity.className
                          )}
                        >
                          {severity.label}
                        </span>
                      </SimpleTooltip>
                      {finding.score && (
                        <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                          {finding.score}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          copyFinding(finding)
                        }}
                        className="flex items-center justify-center rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                        aria-label={t("report.copyFinding")}
                        title={t("report.copyFinding")}
                      >
                        <HugeiconsIcon
                          icon={copied[finding.id] ? CheckIcon : Copy01Icon}
                          className="size-3.5"
                        />
                      </button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div className="flex flex-wrap gap-1">
                    <FieldBadge label={t("field.agent")} value={finding.agent} />
                    <FieldBadge label={t("field.tool")} value={finding.tool} />
                    <FieldBadge
                      label={t("field.category")}
                      value={finding.category}
                    />
                    <FieldBadge
                      label={t("field.confidence")}
                      value={finding.confidence}
                    />
                    <FieldBadge label={t("field.cwe")} value={finding.cwe} />
                  </div>
                  <div>
                    <div className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                      {t("section.description")}
                    </div>
                    <Markdown>{finding.description}</Markdown>
                  </div>
                  {finding.remediation && (
                    <div>
                      <div className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                        {t("section.remediation")}
                      </div>
                      <Markdown>{finding.remediation}</Markdown>
                    </div>
                  )}
                </CardContent>
                {finding.trace.length > 0 && (
                  <CardFooter className="flex-col items-start border-t pt-3">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        toggleFinding(finding.id)
                      }}
                      className="flex w-full items-center justify-between text-xs font-medium hover:text-primary"
                    >
                      <span>{t("section.steps")}</span>
                      <HugeiconsIcon
                        icon={ArrowDown01Icon}
                        className={cn(
                          "size-3.5 transition-transform",
                          expanded[finding.id] && "rotate-180"
                        )}
                      />
                    </button>
                    {expanded[finding.id] && (
                      <div className="mt-3 w-full">
                        <ol className="list-decimal space-y-2 pl-4 text-xs">
                          {finding.trace.map((step, idx) => (
                            <li key={idx}>
                              <Markdown>{step}</Markdown>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </CardFooter>
                )}
              </Card>
            )
          })}
        </div>
        )}
      </ScrollArea>
    </div>
  )
}
