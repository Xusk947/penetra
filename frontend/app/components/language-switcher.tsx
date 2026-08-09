"use client"

import { HugeiconsIcon } from "@hugeicons/react"
import { Globe02Icon } from "@hugeicons/core-free-icons"

import { LOCALES, LOCALE_NAMES, useI18n } from "~/lib/i18n"
import { cn } from "~/lib/utils"

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n()

  return (
    <div className="mt-auto border-t border-border p-2">
      <div className="mb-1 flex items-center gap-1.5 px-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
        <HugeiconsIcon icon={Globe02Icon} className="size-3" />
        {t("lang.label")}
      </div>
      <div className="flex gap-1 rounded-lg bg-muted/50 p-1">
        {LOCALES.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setLocale(option)}
            aria-pressed={option === locale}
            title={LOCALE_NAMES[option]}
            className={cn(
              "flex flex-1 items-center justify-center rounded-md px-2 py-1.5 text-xs font-medium uppercase transition-colors",
              option === locale
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}
