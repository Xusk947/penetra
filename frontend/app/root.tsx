import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  isRouteErrorResponse,
  useLoaderData,
  useRouteLoaderData,
} from "react-router"

import type { Route } from "./+types/root"
import "./app.css"
import {
  DEFAULT_LOCALE,
  I18nProvider,
  getLocaleFromRequest,
  isLocale,
} from "~/lib/i18n"

export function loader({ request }: Route.LoaderArgs) {
  return { locale: getLocaleFromRequest(request) }
}

export function Layout({ children }: { children: React.ReactNode }) {
  const data = useRouteLoaderData("root") as { locale?: string } | undefined
  const lang = isLocale(data?.locale) ? data.locale : DEFAULT_LOCALE
  return (
    <html lang={lang}>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  )
}

export default function App() {
  const { locale } = useLoaderData<typeof loader>()
  return (
    <I18nProvider initialLocale={isLocale(locale) ? locale : DEFAULT_LOCALE}>
      <Outlet />
    </I18nProvider>
  )
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!"
  let details = "An unexpected error occurred."
  let stack: string | undefined

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error"
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message
    stack = error.stack
  }

  return (
    <main className="container mx-auto p-4 pt-16">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full overflow-x-auto p-4">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  )
}
