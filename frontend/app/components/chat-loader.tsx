import { useRef } from "react"
import { gsap } from "gsap"
import { useGSAP } from "@gsap/react"

import { cn } from "~/lib/utils"

export type ChatLoaderStatus = "submitted" | "streaming" | "ready" | "error"

const statusLabel: Record<ChatLoaderStatus, string> = {
  submitted: "Думаю…",
  streaming: "Печатаю…",
  ready: "",
  error: "",
}

export function ChatLoader({
  status,
  label: labelProp,
  className,
}: {
  status: ChatLoaderStatus
  label?: string
  className?: string
}) {
  const label = labelProp ?? statusLabel[status] ?? "Загрузка…"
  const containerRef = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const dots = containerRef.current?.querySelectorAll(".chat-loader-dot")
      if (!dots || dots.length === 0) return

      gsap.to(dots, {
        y: -10,
        duration: 0.55,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true,
        stagger: { each: 0.12 },
      })

      gsap.to(dots, {
        opacity: 0.35,
        duration: 0.55,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true,
        stagger: { each: 0.12 },
      })
    },
    { scope: containerRef }
  )

  return (
    <div
      ref={containerRef}
      className={cn("flex items-center gap-3 py-2", className)}
      role="status"
      aria-live="polite"
    >
      <div className="flex h-4 items-end gap-1">
        <span className="chat-loader-dot size-2 rounded-full bg-muted-foreground" />
        <span className="chat-loader-dot size-2 rounded-full bg-muted-foreground" />
        <span className="chat-loader-dot size-2 rounded-full bg-muted-foreground" />
      </div>
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  )
}
