// Same-origin '/api' in production (Caddy) and in dev (Vite proxy).
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

// How often we re-fetch authoritative pet state from the server.
export const POLL_MS = 5000

// Egg hatch timeline (seconds). Must match HATCH_SECONDS in the backend's
// pet_logic.py. Phases: idle -> rumbling (1/3) -> cracking (2/3) -> hatch.
export const HATCH_SECONDS = 30

export const COLORS = [
  { id: 'teal', label: 'Teal' },
  { id: 'pink', label: 'Pink' },
  { id: 'butter', label: 'Butter' },
  { id: 'grape', label: 'Grape' },
  { id: 'sky', label: 'Sky' },
  { id: 'charcoal', label: 'Charcoal' },
]
