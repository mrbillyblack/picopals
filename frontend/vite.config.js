import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// During `vite dev` we proxy /api to the FastAPI backend so the browser talks
// same-origin (no CORS) exactly like it will in production behind Caddy.
export default defineConfig({
  plugins: [tailwindcss()],
  // No inline module-preload polyfill, so the build needs no inline <script>
  // and works under a strict Content-Security-Policy (script-src 'self').
  build: {
    modulePreload: { polyfill: false },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
