import { API_BASE } from './config.js'

async function request(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail || detail
    } catch {
      /* ignore */
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const api = {
  createUser: () => request('/users', { method: 'POST' }),
  getUser: (id) => request(`/users/${id}`),
  recover: (recovery_code) =>
    request('/users/recover', {
      method: 'POST',
      body: JSON.stringify({ recovery_code }),
    }),
  getPet: (id) => request(`/pets/${id}`),
  hatch: (id) => request(`/pets/${id}/hatch`, { method: 'POST' }),
  action: (id, action) =>
    request(`/pets/${id}/action`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),
  setName: (id, name) =>
    request(`/pets/${id}/name`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  reset: (id) => request(`/pets/${id}/reset`, { method: 'POST' }),
}
