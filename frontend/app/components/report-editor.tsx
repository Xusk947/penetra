"use client"

import { useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  Add01Icon,
  Cancel01Icon,
  Delete02Icon,
  FloppyDiskIcon,
  Loading01Icon,
} from "@hugeicons/core-free-icons"

import { Button } from "~/components/ui/button"
import { Card, CardContent, CardHeader } from "~/components/ui/card"
import { Input } from "~/components/ui/input"
import { Textarea } from "~/components/ui/textarea"
import { useI18n } from "~/lib/i18n"
import { cn } from "~/lib/utils"

export interface EditableFinding {
  id: string
  title: string
  severity: string
  confidence: string
  description: string
  cwe: string
  remediation: string
  category: string
  score: number | null
  steps: string[]
  agent: string
  tool: string
}

const SEVERITIES = ["critical", "high", "medium", "low", "info"]
const CONFIDENCES = ["certain", "high", "medium", "low"]

function newFindingId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(4))
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase()
  return `VULN-${hex}`
}

const selectClassName =
  "h-7 rounded-md border border-input bg-input/20 px-1.5 text-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
      {children}
    </div>
  )
}

interface ReportEditorProps {
  initialFindings: EditableFinding[]
  saving: boolean
  onSave: (findings: EditableFinding[]) => void
  onCancel: () => void
}

export function ReportEditor({
  initialFindings,
  saving,
  onSave,
  onCancel,
}: ReportEditorProps) {
  const { t } = useI18n()
  const [findings, setFindings] = useState<EditableFinding[]>(initialFindings)

  const updateFinding = (
    id: string,
    patch: Partial<EditableFinding>
  ) => {
    setFindings((prev) =>
      prev.map((finding) =>
        finding.id === id ? { ...finding, ...patch } : finding
      )
    )
  }

  const removeFinding = (id: string) => {
    setFindings((prev) => prev.filter((finding) => finding.id !== id))
  }

  const addFinding = () => {
    setFindings((prev) => [
      ...prev,
      {
        id: newFindingId(),
        title: t("editor.newFindingTitle"),
        severity: "medium",
        confidence: "certain",
        description: "",
        cwe: "",
        remediation: "",
        category: "general",
        score: 3,
        steps: [],
        agent: "admin",
        tool: "manual",
      },
    ])
  }

  return (
    <div className="space-y-4 pb-2">
      <div className="flex items-center justify-between gap-2">
        <Button
          variant="secondary"
          onPress={addFinding}
          className="flex items-center gap-1 text-xs"
        >
          <HugeiconsIcon icon={Add01Icon} className="size-3.5" />
          {t("editor.addFinding")}
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onPress={onCancel}
            isDisabled={saving}
            className="flex items-center gap-1 text-xs"
          >
            <HugeiconsIcon icon={Cancel01Icon} className="size-3.5" />
            {t("editor.cancel")}
          </Button>
          <Button
            onPress={() => onSave(findings)}
            isDisabled={saving}
            className="flex items-center gap-1 text-xs"
          >
            <HugeiconsIcon
              icon={saving ? Loading01Icon : FloppyDiskIcon}
              className={cn("size-3.5", saving && "animate-spin")}
            />
            {t("editor.save")}
          </Button>
        </div>
      </div>

      {findings.length === 0 && (
        <div className="rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">
          {t("editor.empty")}
        </div>
      )}

      {findings.map((finding, index) => (
        <Card key={finding.id} className="bg-card">
          <CardHeader className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {index + 1}.
              </span>
              <Input
                value={finding.title}
                onChange={(event) =>
                  updateFinding(finding.id, { title: event.target.value })
                }
                placeholder={t("editor.titlePlaceholder")}
                className="flex-1"
              />
              <select
                value={finding.severity}
                onChange={(event) =>
                  updateFinding(finding.id, { severity: event.target.value })
                }
                className={selectClassName}
                aria-label={t("editor.severity")}
              >
                {SEVERITIES.map((severity) => (
                  <option key={severity} value={severity}>
                    {severity}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removeFinding(finding.id)}
                className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
                aria-label={t("editor.removeFinding")}
                title={t("editor.removeFinding")}
              >
                <HugeiconsIcon icon={Delete02Icon} className="size-3.5" />
              </button>
            </div>
            <div className="text-[10px] text-muted-foreground">
              {finding.id}
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <div>
                <FieldLabel>{t("field.agent")}</FieldLabel>
                <Input
                  value={finding.agent}
                  onChange={(event) =>
                    updateFinding(finding.id, { agent: event.target.value })
                  }
                  placeholder="client/server/iot"
                />
              </div>
              <div>
                <FieldLabel>{t("field.tool")}</FieldLabel>
                <Input
                  value={finding.tool}
                  onChange={(event) =>
                    updateFinding(finding.id, { tool: event.target.value })
                  }
                  placeholder="check name"
                />
              </div>
              <div>
                <FieldLabel>{t("field.category")}</FieldLabel>
                <Input
                  value={finding.category}
                  onChange={(event) =>
                    updateFinding(finding.id, { category: event.target.value })
                  }
                  placeholder="general"
                />
              </div>
              <div>
                <FieldLabel>{t("field.confidence")}</FieldLabel>
                <select
                  value={finding.confidence}
                  onChange={(event) =>
                    updateFinding(finding.id, {
                      confidence: event.target.value,
                    })
                  }
                  className={cn(selectClassName, "w-full")}
                  aria-label={t("field.confidence")}
                >
                  {CONFIDENCES.map((confidence) => (
                    <option key={confidence} value={confidence}>
                      {confidence}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <FieldLabel>{t("editor.scoreLabel")}</FieldLabel>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={finding.score === null ? "" : String(finding.score)}
                  onChange={(event) => {
                    const raw = event.target.value
                    if (raw === "") {
                      updateFinding(finding.id, { score: null })
                      return
                    }
                    const value = Math.max(
                      1,
                      Math.min(5, Math.round(Number(raw)))
                    )
                    updateFinding(finding.id, {
                      score: Number.isNaN(value) ? null : value,
                    })
                  }}
                />
              </div>
              <div>
                <FieldLabel>{t("field.cwe")}</FieldLabel>
                <Input
                  value={finding.cwe}
                  onChange={(event) =>
                    updateFinding(finding.id, { cwe: event.target.value })
                  }
                  placeholder="CWE-79"
                />
              </div>
            </div>

            <div>
              <FieldLabel>{t("section.description")}</FieldLabel>
              <Textarea
                value={finding.description}
                onChange={(event) =>
                  updateFinding(finding.id, {
                    description: event.target.value,
                  })
                }
                placeholder={t("editor.descPlaceholder")}
              />
            </div>

            <div>
              <FieldLabel>{t("editor.stepsLabel")}</FieldLabel>
              <Textarea
                value={finding.steps.join("\n")}
                onChange={(event) =>
                  updateFinding(finding.id, {
                    steps: event.target.value
                      .split("\n")
                      .map((step) => step.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="GET /login&#10;POST username=..."
              />
            </div>

            <div>
              <FieldLabel>{t("section.remediation")}</FieldLabel>
              <Textarea
                value={finding.remediation}
                onChange={(event) =>
                  updateFinding(finding.id, {
                    remediation: event.target.value,
                  })
                }
                placeholder={t("editor.remPlaceholder")}
              />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
