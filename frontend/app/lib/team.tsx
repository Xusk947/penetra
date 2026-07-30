"use client"

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

export type TeamId = "admin" | "enterprise" | "client"

export interface Team {
  id: TeamId
  label: string
  description: string
  /** May ask the chat agent to run pentests / generate reports. */
  canRunScans: boolean
  /** May manually edit report findings and add new ones. */
  canEditReports: boolean
  /** May mark a report as officially verified by the Admin Team. */
  canVerify: boolean
  /** May delete chats and reports. */
  canDelete: boolean
}

export const TEAMS: Team[] = [
  {
    id: "admin",
    label: "Admin Team",
    description: "Сканы, редактирование и верификация репортов",
    canRunScans: true,
    canEditReports: true,
    canVerify: true,
    canDelete: true,
  },
  {
    id: "enterprise",
    label: "Enterprise Team",
    description: "Запуск сканов и генерация репортов",
    canRunScans: true,
    canEditReports: false,
    canVerify: false,
    canDelete: true,
  },
  {
    id: "client",
    label: "Client Team",
    description: "Чат и просмотр репортов, без запуска сканов",
    canRunScans: false,
    canEditReports: false,
    canVerify: false,
    canDelete: false,
  },
]

const STORAGE_KEY = "team"

function isTeamId(value: string | null): value is TeamId {
  return value === "admin" || value === "enterprise" || value === "client"
}

interface TeamContextValue {
  team: Team
  setTeam: (id: TeamId) => void
}

const TeamContext = createContext<TeamContextValue | null>(null)

export function TeamProvider({ children }: { children: ReactNode }) {
  const [teamId, setTeamId] = useState<TeamId>("admin")

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (isTeamId(stored)) setTeamId(stored)
  }, [])

  const setTeam = (id: TeamId) => {
    setTeamId(id)
    localStorage.setItem(STORAGE_KEY, id)
  }

  const team = TEAMS.find((t) => t.id === teamId) ?? TEAMS[0]

  return (
    <TeamContext.Provider value={{ team, setTeam }}>
      {children}
    </TeamContext.Provider>
  )
}

export function useTeam() {
  const ctx = useContext(TeamContext)
  if (!ctx) throw new Error("useTeam must be used within TeamProvider")
  return ctx
}
