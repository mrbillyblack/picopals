// Same-origin '/api' in production (Caddy) and in dev (Vite proxy).
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

// How often we re-fetch authoritative pet state from the server.
export const POLL_MS = 5000

export const COLORS = [
  { id: 'teal', label: 'Teal' },
  { id: 'pink', label: 'Pink' },
  { id: 'butter', label: 'Butter' },
  { id: 'grape', label: 'Grape' },
  { id: 'sky', label: 'Sky' },
  { id: 'charcoal', label: 'Charcoal' },
]
