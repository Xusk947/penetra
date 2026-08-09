"use client"

import { useEffect } from "react"

import { Button } from "~/components/ui/button"
import { useI18n } from "~/lib/i18n"

interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText,
  cancelText,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useI18n()
  useEffect(() => {
    if (!isOpen) return

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel()
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [isOpen, onCancel])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onCancel}
    >
      <div
        role="alertdialog"
        className="w-full max-w-sm rounded-xl bg-card p-4 text-card-foreground shadow-lg ring-1 ring-foreground/10"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="mb-2 font-heading text-sm font-medium">{title}</h2>
        <p className="mb-4 text-xs text-muted-foreground">{message}</p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onPress={onCancel}>
            {cancelText ?? t("confirm.cancel")}
          </Button>
          <Button variant="destructive" onPress={onConfirm}>
            {confirmText ?? t("confirm.delete")}
          </Button>
        </div>
      </div>
    </div>
  )
}
