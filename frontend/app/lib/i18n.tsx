"use client"

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"

export const LOCALES = ["en", "ru", "uz"] as const
export type Locale = (typeof LOCALES)[number]
export const DEFAULT_LOCALE: Locale = "ru"
export const LOCALE_COOKIE = "lang"

/** Native language names shown in the switcher (same in every locale). */
export const LOCALE_NAMES: Record<Locale, string> = {
  en: "English",
  ru: "Русский",
  uz: "Oʻzbek",
}

/** BCP-47 tags used for Intl date/number formatting. */
export const LOCALE_DATE_TAG: Record<Locale, string> = {
  en: "en-US",
  ru: "ru-RU",
  uz: "uz-UZ",
}

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value)
}

/** Parse the `lang` cookie from a request (server-side loaders). */
export function getLocaleFromRequest(request: Request): Locale {
  const cookie = request.headers.get("Cookie") ?? ""
  const match = cookie.match(/(?:^|;\s*)lang=([^;]+)/)
  const value = match ? decodeURIComponent(match[1]) : null
  return isLocale(value) ? value : DEFAULT_LOCALE
}

type Dict = Record<string, string>

const en: Dict = {
  // Generic
  "confirm.delete": "Delete",
  "confirm.cancel": "Cancel",

  // Navigation / sidebar
  "nav.chat": "Chat",
  "nav.reports": "Reports",
  "sidebar.menu": "Sidebar menu",
  "sidebar.open": "Open sidebar",
  "sidebar.collapse": "Collapse sidebar",
  "sidebar.newChat": "New chat",
  "sidebar.deleteChat": "Delete chat",
  "sidebar.deleteReport": "Delete report",
  "sidebar.noChats": "No chats",
  "sidebar.noReports": "No reports",
  "sidebar.findings": "{count} findings",
  "sidebar.confirmDeleteTitle": "Confirm deletion",
  "sidebar.confirmDeleteMessage": "Delete “{title}”? This action is irreversible.",

  // Teams
  "team.admin.desc": "Scans, editing and report verification",
  "team.enterprise.desc": "Run scans and generate reports",
  "team.client.desc": "Chat and view reports, no scan runs",

  // Language switcher
  "lang.label": "Language",

  // Chat / tools
  "chat.header.new": "New chat",
  "tool.run_pentest": "Vulnerability scan",
  "tool.run_osint": "OSINT recon",
  "tool.run_research": "Research",
  "tool.running": "Running {tool}",
  "tool.inputParams": "Input parameters",
  "tool.result": "Result",
  "agent.doneWithFindings": "done · {count} findings",
  "agent.inProgress": "in progress…",
  "agent.finding": "Finding",
  "agent.finished": "Agent {agent} finished",
  "agent.findingsSuffix": ", findings found: {count}",
  "agent.errorSuffix": " · error: {error}",
  "status.error": "error",
  "status.done": "done",
  "status.working": "working",
  "attachments.title": "Attached documents",
  "report.defaultTitle": "Penetration test report",
  "attachment.open": "Open report",
  "attachment.downloadMd": "Download Markdown",
  "prompt.placeholderRun": "What are we checking?",
  "prompt.placeholderNoRun": "Can you check the system?",
  "prompt.placeholderRunLong":
    "Type a request (Enter to send, Shift+Enter for a new line)",
  "prompt.placeholderNoRunLong":
    "Ask about reports (running scans — Admin/Enterprise only)",
  "prompt.default": "Type a request...",
  "prompt.send": "Send",
  "chat.errorPrefix": "Error: {msg}",
  "chat.errorFallback": "Failed to get a response",

  // Loader
  "loader.thinking": "Thinking…",
  "loader.typing": "Typing…",
  "loader.loading": "Loading…",

  // Report page
  "severity.critical": "Critical",
  "severity.high": "High",
  "severity.medium": "Medium",
  "severity.low": "Low",
  "severity.info": "Info",
  "severity.critical.desc":
    "Maximum risk: system compromise, remote code execution, full data access.",
  "severity.high.desc":
    "Serious risk: sensitive data disclosure, privilege escalation.",
  "severity.medium.desc":
    "Moderate risk: requires extra conditions or has limited impact.",
  "severity.low.desc": "Low risk: hard to exploit or minimal consequences.",
  "severity.info.desc":
    "Informational finding: no direct threat, but useful for understanding the system.",
  "severity.unknown.desc": "Unknown severity label.",
  "field.agent": "Agent",
  "field.tool": "Tool",
  "field.category": "Category",
  "field.confidence": "Confidence",
  "field.cwe": "CWE",
  "field.severity": "Severity",
  "field.score": "Score",
  "section.description": "Description",
  "section.remediation": "Remediation",
  "section.steps": "Steps",
  "report.selectPrompt": "Select a report in the sidebar",
  "report.notFound": "Report not found",
  "report.saveError": "Failed to save the report",
  "report.verifyError": "Failed to update verification status",
  "report.verifiedTooltipAt": "Verified manually: {date}",
  "report.verifiedTooltip": "Verified manually by Admin Team",
  "report.verifiedByAdmin": "Verified by Admin Team",
  "report.unverify": "Unverify",
  "report.verify": "Verified",
  "report.view": "View",
  "report.edit": "Edit",
  "report.copyFinding": "Copy finding",

  // Report editor
  "editor.addFinding": "Add finding",
  "editor.cancel": "Cancel",
  "editor.save": "Save",
  "editor.empty": "No findings — add the first one manually",
  "editor.newFindingTitle": "New finding",
  "editor.titlePlaceholder": "Finding title",
  "editor.severity": "Severity",
  "editor.removeFinding": "Delete finding",
  "editor.scoreLabel": "Score (1–5)",
  "editor.descPlaceholder": "Vulnerability description (markdown)",
  "editor.stepsLabel": "Steps (one per line)",
  "editor.remPlaceholder": "How to fix (markdown)",

  // Server-generated strings (chat routes)
  "chat.threadFallback": "Chat {id}",
  "error.noMessages": "Error: no messages received.",
  "error.threadCreate": "Thread creation error ({status}): {detail}",
  "error.backend": "Backend error ({status}): {detail}",
  "error.noBody": "Error: backend returned no response body.",
  "error.connect":
    "Failed to connect to the backend ({url}): {message}. Start langgraph dev in the backend folder.",
}

const ru: Dict = {
  "confirm.delete": "Удалить",
  "confirm.cancel": "Отмена",

  "nav.chat": "Чат",
  "nav.reports": "Репорты",
  "sidebar.menu": "Боковое меню",
  "sidebar.open": "Открыть боковую панель",
  "sidebar.collapse": "Свернуть боковую панель",
  "sidebar.newChat": "Новый чат",
  "sidebar.deleteChat": "Удалить чат",
  "sidebar.deleteReport": "Удалить репорт",
  "sidebar.noChats": "Нет чатов",
  "sidebar.noReports": "Нет репортов",
  "sidebar.findings": "{count} находок",
  "sidebar.confirmDeleteTitle": "Подтвердите удаление",
  "sidebar.confirmDeleteMessage": "Точно удалить «{title}»? Действие необратимо.",

  "team.admin.desc": "Сканы, редактирование и верификация репортов",
  "team.enterprise.desc": "Запуск сканов и генерация репортов",
  "team.client.desc": "Чат и просмотр репортов, без запуска сканов",

  "lang.label": "Язык",

  "chat.header.new": "Новый чат",
  "tool.run_pentest": "Тест по поиску уязвимостей",
  "tool.run_osint": "OSINT-разведка",
  "tool.run_research": "Исследование",
  "tool.running": "Запущен {tool}",
  "tool.inputParams": "Входные параметры",
  "tool.result": "Результат",
  "agent.doneWithFindings": "завершён · {count} находок",
  "agent.inProgress": "в работе…",
  "agent.finding": "Находка",
  "agent.finished": "Агент {agent} завершил работу",
  "agent.findingsSuffix": ", найдено находок: {count}",
  "agent.errorSuffix": " · ошибка: {error}",
  "status.error": "ошибка",
  "status.done": "готово",
  "status.working": "работа",
  "attachments.title": "Прикреплённые документы",
  "report.defaultTitle": "Отчёт о тесте на проникновение",
  "attachment.open": "Открыть отчёт",
  "attachment.downloadMd": "Скачать Markdown",
  "prompt.placeholderRun": "Что проверим?",
  "prompt.placeholderNoRun": "Можешь проверить систему?",
  "prompt.placeholderRunLong":
    "Напиши запрос (Enter — отправить, Shift+Enter — новая строка)",
  "prompt.placeholderNoRunLong":
    "Спроси про репорты (запуск сканов — только Admin/Enterprise)",
  "prompt.default": "Напиши запрос...",
  "prompt.send": "Отправить",
  "chat.errorPrefix": "Ошибка: {msg}",
  "chat.errorFallback": "Не удалось получить ответ",

  "loader.thinking": "Думаю…",
  "loader.typing": "Печатаю…",
  "loader.loading": "Загрузка…",

  "severity.critical": "Критический",
  "severity.high": "Высокий",
  "severity.medium": "Средний",
  "severity.low": "Низкий",
  "severity.info": "Инфо",
  "severity.critical.desc":
    "Максимальный риск: компрометация системы, удалённое выполнение кода, полный доступ к данным.",
  "severity.high.desc":
    "Серьёзный риск: раскрытие конфиденциальных данных, повышение привилегий.",
  "severity.medium.desc":
    "Умеренный риск: требует дополнительных условий или имеет ограниченное воздействие.",
  "severity.low.desc":
    "Низкий риск: сложная эксплуатация или минимальные последствия.",
  "severity.info.desc":
    "Информационная находка: прямой угрозы нет, но полезна для понимания системы.",
  "severity.unknown.desc": "Неизвестная метка серьёзности.",
  "field.agent": "Агент",
  "field.tool": "Инструмент",
  "field.category": "Категория",
  "field.confidence": "Уверенность",
  "field.cwe": "CWE",
  "field.severity": "Серьёзность",
  "field.score": "Score",
  "section.description": "Описание",
  "section.remediation": "Рекомендации",
  "section.steps": "Шаги",
  "report.selectPrompt": "Выберите репорт в боковой панели",
  "report.notFound": "Репорт не найден",
  "report.saveError": "Не удалось сохранить репорт",
  "report.verifyError": "Не удалось обновить статус верификации",
  "report.verifiedTooltipAt": "Проверено вручную: {date}",
  "report.verifiedTooltip": "Проверено вручную Admin Team",
  "report.verifiedByAdmin": "Проверено Admin Team",
  "report.unverify": "Снять проверку",
  "report.verify": "Проверено",
  "report.view": "Просмотр",
  "report.edit": "Редактировать",
  "report.copyFinding": "Скопировать уязвимость",

  "editor.addFinding": "Добавить находку",
  "editor.cancel": "Отмена",
  "editor.save": "Сохранить",
  "editor.empty": "Нет находок — добавьте первую вручную",
  "editor.newFindingTitle": "Новая находка",
  "editor.titlePlaceholder": "Название находки",
  "editor.severity": "Серьёзность",
  "editor.removeFinding": "Удалить находку",
  "editor.scoreLabel": "Score (1–5)",
  "editor.descPlaceholder": "Описание уязвимости (markdown)",
  "editor.stepsLabel": "Шаги (по одному на строку)",
  "editor.remPlaceholder": "Как исправить (markdown)",

  "chat.threadFallback": "Чат {id}",
  "error.noMessages": "Ошибка: не получено ни одного сообщения.",
  "error.threadCreate": "Ошибка создания треда ({status}): {detail}",
  "error.backend": "Ошибка бэкенда ({status}): {detail}",
  "error.noBody": "Ошибка: бэкенд не вернул тело ответа.",
  "error.connect":
    "Не удалось подключиться к бэкенду ({url}): {message}. Запусти langgraph dev в папке backend.",
}

const uz: Dict = {
  "confirm.delete": "Oʻchirish",
  "confirm.cancel": "Bekor qilish",

  "nav.chat": "Chat",
  "nav.reports": "Hisobotlar",
  "sidebar.menu": "Yon menyu",
  "sidebar.open": "Yon panelni ochish",
  "sidebar.collapse": "Yon panelni yigʻish",
  "sidebar.newChat": "Yangi chat",
  "sidebar.deleteChat": "Chatni oʻchirish",
  "sidebar.deleteReport": "Hisobotni oʻchirish",
  "sidebar.noChats": "Chatlar yoʻq",
  "sidebar.noReports": "Hisobotlar yoʻq",
  "sidebar.findings": "{count} ta topilma",
  "sidebar.confirmDeleteTitle": "Oʻchirishni tasdiqlang",
  "sidebar.confirmDeleteMessage":
    "“{title}” haqiqatan oʻchirilsinmi? Bu amalni qaytarib boʻlmaydi.",

  "team.admin.desc": "Skanerlar, tahrirlash va hisobotlarni tasdiqlash",
  "team.enterprise.desc": "Skanerlarni ishga tushirish va hisobot yaratish",
  "team.client.desc": "Chat va hisobotlarni koʻrish, skanersiz",

  "lang.label": "Til",

  "chat.header.new": "Yangi chat",
  "tool.run_pentest": "Zaifliklarni qidirish testi",
  "tool.run_osint": "OSINT razvedka",
  "tool.run_research": "Tadqiqot",
  "tool.running": "{tool} ishga tushdi",
  "tool.inputParams": "Kirish parametrlari",
  "tool.result": "Natija",
  "agent.doneWithFindings": "tugadi · {count} ta topilma",
  "agent.inProgress": "jarayonda…",
  "agent.finding": "Topilma",
  "agent.finished": "{agent} agenti ishini tugatdi",
  "agent.findingsSuffix": ", topilgan topilmalar: {count}",
  "agent.errorSuffix": " · xatolik: {error}",
  "status.error": "xatolik",
  "status.done": "tayyor",
  "status.working": "ishlayapti",
  "attachments.title": "Biriktirilgan hujjatlar",
  "report.defaultTitle": "Penetratsion test hisoboti",
  "attachment.open": "Hisobotni ochish",
  "attachment.downloadMd": "Markdown yuklab olish",
  "prompt.placeholderRun": "Nimani tekshiramiz?",
  "prompt.placeholderNoRun": "Tizimni tekshira olasizmi?",
  "prompt.placeholderRunLong":
    "Soʻrov yozing (Enter — yuborish, Shift+Enter — yangi qator)",
  "prompt.placeholderNoRunLong":
    "Hisobotlar haqida soʻrang (skaner faqat Admin/Enterprise uchun)",
  "prompt.default": "Soʻrov yozing...",
  "prompt.send": "Yuborish",
  "chat.errorPrefix": "Xatolik: {msg}",
  "chat.errorFallback": "Javob olinmadi",

  "loader.thinking": "Oʻylayapman…",
  "loader.typing": "Yozayapman…",
  "loader.loading": "Yuklanmoqda…",

  "severity.critical": "Kritik",
  "severity.high": "Yuqori",
  "severity.medium": "Oʻrta",
  "severity.low": "Past",
  "severity.info": "Maʼlumot",
  "severity.critical.desc":
    "Maksimal xavf: tizim buzilishi, masofadan kod bajarish, maʼlumotlarga toʻliq kirish.",
  "severity.high.desc":
    "Jiddiy xavf: maxfiy maʼlumotlar oshkor boʻlishi, imtiyozlarni oshirish.",
  "severity.medium.desc":
    "Oʻrtacha xavf: qoʻshimcha shartlar talab qiladi yoki taʼsiri cheklangan.",
  "severity.low.desc":
    "Past xavf: ekspluatatsiya qiyin yoki oqibatlari minimal.",
  "severity.info.desc":
    "Maʼlumot topilmasi: bevosita tahdid yoʻq, ammo tizimni tushunish uchun foydali.",
  "severity.unknown.desc": "Nomaʼlum xavf darajasi.",
  "field.agent": "Agent",
  "field.tool": "Vosita",
  "field.category": "Kategoriya",
  "field.confidence": "Ishonch",
  "field.cwe": "CWE",
  "field.severity": "Xavf darajasi",
  "field.score": "Score",
  "section.description": "Tavsif",
  "section.remediation": "Tavsiyalar",
  "section.steps": "Qadamlar",
  "report.selectPrompt": "Yon paneldan hisobotni tanlang",
  "report.notFound": "Hisobot topilmadi",
  "report.saveError": "Hisobotni saqlab boʻlmadi",
  "report.verifyError": "Tasdiqlash holatini yangilab boʻlmadi",
  "report.verifiedTooltipAt": "Qoʻlda tasdiqlangan: {date}",
  "report.verifiedTooltip": "Admin Team tomonidan qoʻlda tasdiqlangan",
  "report.verifiedByAdmin": "Admin Team tomonidan tasdiqlangan",
  "report.unverify": "Tasdiqni olib tashlash",
  "report.verify": "Tasdiqlangan",
  "report.view": "Koʻrish",
  "report.edit": "Tahrirlash",
  "report.copyFinding": "Topilmani nusxalash",

  "editor.addFinding": "Topilma qoʻshish",
  "editor.cancel": "Bekor qilish",
  "editor.save": "Saqlash",
  "editor.empty": "Topilmalar yoʻq — birinchisini qoʻlda qoʻshing",
  "editor.newFindingTitle": "Yangi topilma",
  "editor.titlePlaceholder": "Topilma nomi",
  "editor.severity": "Xavf darajasi",
  "editor.removeFinding": "Topilmani oʻchirish",
  "editor.scoreLabel": "Score (1–5)",
  "editor.descPlaceholder": "Zaiflik tavsifi (markdown)",
  "editor.stepsLabel": "Qadamlar (har biri alohida qatorda)",
  "editor.remPlaceholder": "Qanday tuzatish (markdown)",

  "chat.threadFallback": "Chat {id}",
  "error.noMessages": "Xatolik: hech qanday xabar kelmadi.",
  "error.threadCreate": "Tred yaratishda xatolik ({status}): {detail}",
  "error.backend": "Backend xatosi ({status}): {detail}",
  "error.noBody": "Xatolik: backend javob tanasini qaytarmadi.",
  "error.connect":
    "Backendga ulanib boʻlmadi ({url}): {message}. backend papkasida langgraph dev ni ishga tushiring.",
}

const translations: Record<Locale, Dict> = { en, ru, uz }

export type TranslateFn = (
  key: string,
  vars?: Record<string, string | number>
) => string

function interpolate(template: string, vars?: Record<string, string | number>) {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match
  )
}

/** Translate a key for a known locale. Usable in server loaders/actions. */
export function translate(
  locale: Locale,
  key: string,
  vars?: Record<string, string | number>
): string {
  const dict = translations[locale] ?? translations[DEFAULT_LOCALE]
  return interpolate(dict[key] ?? translations[DEFAULT_LOCALE][key] ?? key, vars)
}

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: TranslateFn
  dateTag: string
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale
  children: ReactNode
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale)

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    if (typeof document !== "undefined") {
      document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=31536000; SameSite=Lax`
      document.documentElement.lang = next
    }
  }, [])

  const value = useMemo<I18nContextValue>(() => {
    const dict = translations[locale]
    const t: TranslateFn = (key, vars) =>
      interpolate(dict[key] ?? translations[DEFAULT_LOCALE][key] ?? key, vars)
    return { locale, setLocale, t, dateTag: LOCALE_DATE_TAG[locale] }
  }, [locale, setLocale])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error("useI18n must be used within I18nProvider")
  return ctx
}
