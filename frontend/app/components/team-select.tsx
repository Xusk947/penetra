"use client"

import { useEffect, useRef, useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowDown01Icon,
  CheckmarkBadge01Icon,
  UserGroupIcon,
} from "@hugeicons/core-free-icons"

import { TEAMS, useTeam } from "~/lib/team"
import { cn } from "~/lib/utils"

export function TeamSelect() {
  const { team, setTeam } = useTeam()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleClick = (event: MouseEvent) => {
      if (
        rootRef.current &&
        event.target instanceof Node &&
        !rootRef.current.contains(event.target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [open])

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 rounded-lg border bg-card px-2.5 py-2 text-left text-xs transition-colors hover:bg-muted"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <HugeiconsIcon
          icon={UserGroupIcon}
          className="size-3.5 shrink-0 text-muted-foreground"
        />
        <span className="flex-1 truncate font-medium">{team.label}</span>
        <HugeiconsIcon
          icon={ArrowDown01Icon}
          className={cn(
            "size-3.5 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute right-0 left-0 z-20 mt-1 flex flex-col gap-0.5 rounded-lg border bg-popover p-1 shadow-lg"
        >
          {TEAMS.map((option) => {
            const isActive = option.id === team.id
            return (
              <button
                key={option.id}
                type="button"
                role="option"
                aria-selected={isActive}
                onClick={() => {
                  setTeam(option.id)
                  setOpen(false)
                }}
                className={cn(
                  "flex items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors",
                  isActive ? "bg-primary/10" : "hover:bg-muted"
                )}
              >
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="text-xs font-medium">{option.label}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {option.description}
                  </span>
                </span>
                {isActive && (
                  <HugeiconsIcon
                    icon={CheckmarkBadge01Icon}
                    className="mt-0.5 size-3.5 shrink-0 text-primary"
                  />
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
