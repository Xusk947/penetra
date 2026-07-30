import { reactRouter } from "@react-router/dev/vite"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

export default defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [tailwindcss(), reactRouter()],
  server: {
    host: "127.0.0.1",
    allowedHosts: ["mine.ru.tuna.am", ".tuna.am"],
  },
})
