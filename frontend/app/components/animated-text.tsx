"use client"

import { useRef } from "react"
import { gsap } from "gsap"
import { useGSAP } from "@gsap/react"

export function AnimatedText({
  text,
  isStreaming = false,
}: {
  text: string
  isStreaming?: boolean
}) {
  const containerRef = useRef<HTMLSpanElement>(null)
  const prevCountRef = useRef(0)

  const words = text.split(" ").filter(Boolean)

  useGSAP(
    () => {
      const spans = containerRef.current?.querySelectorAll(".word")
      if (!spans) return

      if (!isStreaming) {
        gsap.set(spans, { opacity: 1, y: 0 })
        prevCountRef.current = spans.length
        return
      }

      const newSpans = Array.from(spans).slice(prevCountRef.current)
      if (newSpans.length === 0) {
        prevCountRef.current = spans.length
        return
      }

      gsap.fromTo(
        newSpans,
        { opacity: 0, y: 4 },
        {
          opacity: 1,
          y: 0,
          duration: 0.2,
          stagger: 0.02,
          ease: "power1.out",
        }
      )

      prevCountRef.current = spans.length
    },
    { scope: containerRef, dependencies: [text, isStreaming] }
  )

  if (!isStreaming) {
    return <>{text}</>
  }

  return (
    <span ref={containerRef} className="whitespace-pre-wrap">
      {words.flatMap((word, index) => [
        <span
          key={index}
          className="word inline-block"
          style={{
            opacity: index < prevCountRef.current ? 1 : 0,
          }}
        >
          {word}
        </span>,
        index < words.length - 1 ? " " : null,
      ])}
    </span>
  )
}
