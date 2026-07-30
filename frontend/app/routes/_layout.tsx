import { Outlet } from "react-router"

import { Sidebar } from "~/components/sidebar"
import { TeamProvider } from "~/lib/team"

export default function Layout() {
  return (
    <TeamProvider>
      <div className="flex h-svh overflow-hidden">
        <Sidebar />
        <main className="flex flex-1 items-center justify-center overflow-hidden bg-secondary p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </TeamProvider>
  )
}
