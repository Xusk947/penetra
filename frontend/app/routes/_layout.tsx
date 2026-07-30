"use client"

import { useState } from "react"
import { Outlet } from "react-router"
import { HugeiconsIcon } from "@hugeicons/react"
import { Menu01Icon } from "@hugeicons/core-free-icons"

import { Sidebar } from "~/components/sidebar"
import { TeamProvider } from "~/lib/team"

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const toggleSidebar = () => setSidebarOpen((prev) => !prev)

  return (
    <TeamProvider>
      <div className="flex h-svh flex-col overflow-hidden lg:flex-row">
        <header className="flex h-12 shrink-0 items-center gap-2 bg-card px-3 lg:hidden">
          <button
            type="button"
            onClick={toggleSidebar}
            className="flex items-center justify-center rounded-md p-1.5 text-foreground hover:bg-muted"
            aria-label="Боковое меню"
          >
            <HugeiconsIcon icon={Menu01Icon} className="size-5" />
          </button>
          <span className="font-heading text-sm font-semibold">Penetra</span>
        </header>

        <Sidebar isOpen={sidebarOpen} onToggle={toggleSidebar} />

        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={toggleSidebar}
          />
        )}

        <main className="flex flex-1 items-center justify-center overflow-hidden bg-secondary p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </TeamProvider>
  )
}
