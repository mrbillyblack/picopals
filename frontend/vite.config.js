import { defineConfig } from 'vite'

// During `vite dev` we proxy /api to the FastAPI backend so the browser talks
// same-origin (no CORS) exactly like it will in production behind Caddy.
export default defineConfig({
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
