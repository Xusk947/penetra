"use client"

import { HugeiconsIcon } from "@hugeicons/react"
import { ArrowUp01Icon } from "@hugeicons/core-free-icons"
import { useRef, type FormEvent, type KeyboardEvent } from "react"

import { Button } from "~/components/ui/button"
import { Textarea } from "~/components/ui/textarea"
import { cn } from "~/lib/utils"

interface PromptFormProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function PromptForm({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Напиши запрос...",
  className,
}: PromptFormProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      const form = (event.target as HTMLTextAreaElement).form
      form?.requestSubmit()
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className={cn(
        "flex w-full items-end gap-2 rounded-[1.75rem] border bg-card p-2",
        className
      )}
    >
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="min-h-0 flex-1 resize-none rounded-2xl border-0 bg-transparent px-3 py-2.5 text-sm focus-visible:ring-0 focus-visible:ring-offset-0"
      />
      <Button
        type="submit"
        size="icon"
        isDisabled={disabled || !value.trim()}
        aria-label="Отправить"
        className="size-9 rounded-full"
      >
        <HugeiconsIcon icon={ArrowUp01Icon} className="size-4" />
      </Button>
    </form>
  )
}
