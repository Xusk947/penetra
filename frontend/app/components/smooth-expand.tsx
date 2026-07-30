"use client"

import { useRef } from "react"
import { gsap } from "gsap"
import { useGSAP } from "@gsap/react"

import { cn } from "~/lib/utils"

export function SmoothExpand({
  children,
  text,
  isStreaming = false,
  className,
}: {
  children: React.ReactNode
  text: string
  isStreaming?: boolean
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const prevHeightRef = useRef(0)

  useGSAP(
    () => {
      const el = ref.current
      if (!el) return

      const target = el.scrollHeight

      if (!isStreaming) {
        gsap.set(el, { maxHeight: "none" })
        prevHeightRef.current = target
        return
      }

      const start = prevHeightRef.current
      if (Math.abs(target - start) < 1) {
        prevHeightRef.current = target
        return
      }

      gsap.fromTo(
        el,
        { maxHeight: start },
        {
          maxHeight: target,
          duration: 0.25,
          ease: "power1.out",
        }
      )

      prevHeightRef.current = target
    },
    { scope: ref, dependencies: [text, isStreaming] }
  )

  return (
    <div ref={ref} className={cn("overflow-hidden", className)}>
      {children}
    </div>
  )
}
