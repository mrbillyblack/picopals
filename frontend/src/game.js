import { api } from './api.js'
import { store } from './store.js'
import { createRenderer } from './render.js'
import { POLL_MS } from './config.js'

// The icon menu printed around the LCD (authentic 3-button navigation).
export const ICONS = [
  { id: 'meal', glyph: '🍚', label: 'Meal', action: 'feed_meal', row: 'top' },
  { id: 'snack', glyph: '🍬', label: 'Snack', action: 'feed_snack', row: 'top' },
  { id: 'play', glyph: '🎮', label: 'Play', action: 'play', row: 'top' },
  { id: 'clean', glyph: '🧹', label: 'Clean', action: 'clean', row: 'top' },
  { id: 'med', glyph: '💊', label: 'Med', action: 'medicine', row: 'bottom' },
  { id: 'light', glyph: '💡', label: 'Light', action: 'toggle_light', row: 'bottom' },
  { id: 'scold', glyph: '📢', label: 'Scold', action: 'discipline', row: 'bottom' },
  { id: 'stats', glyph: '📊', label: 'Stats', action: '__status__', row: 'bottom' },
]

export function createGame({ canvas, topRow, bottomRow, getDark, toast }) {
  const renderer = createRenderer(canvas)

  let view = null
  let userId = null
  let clockOffset = 0 // serverTime - localTime (seconds)
  let mode = 'main' // 'main' | 'status'
  let selected = 0
  let hatchRequested = false
  let busy = false

  // ---- icon strip ------------------------------------------------------
  function buildIconStrip() {
    for (const rowEl of [topRow, bottomRow]) rowEl.innerHTML = ''
    ICONS.forEach((icon, i) => {
      const el = document.createElement('button')
      el.className = 'icon'
      el.dataset.index = String(i)
      el.innerHTML = `<span class="icon__glyph">${icon.glyph}</span><span class="icon__label">${icon.label}</span>`
      el.addEventListener('click', () => {
        selected = i
        select()
      })
      ;(icon.row === 'top' ? topRow : bottomRow).appendChild(el)
    })
    paintSelection()
  }

  function paintSelection() {
    document.querySelectorAll('.icon').forEach((el) => {
      el.classList.toggle('icon--sel', Number(el.dataset.index) === selected)
    })
  }

  // ---- time helpers ----------------------------------------------------
  const serverNow = () => Date.now() / 1000 + clockOffset
  const eggElapsed = () => (view ? serverNow() - view.born_at : 0)

  function adopt(payload) {
    // payload: { user_id, recovery_code?, pet }
    if (payload.user_id) userId = payload.user_id
    if (payload.recovery_code) store.setRecoveryCode(payload.recovery_code)
    if (userId) store.setUserId(userId)
    setView(payload.pet)
  }

  function setView(pet) {
    view = pet
    if (pet && pet.server_time) clockOffset = pet.server_time - Date.now() / 1000
    if (pet && pet.species !== 'egg') hatchRequested = false
  }

  // ---- bootstrap -------------------------------------------------------
  async function start() {
    const existing = store.getUserId()
    if (existing) {
      try {
        const data = await api.getUser(existing)
        userId = existing
        adopt(data)
      } catch (err) {
        if (err.status === 404) await createFresh()
        else throw err
      }
    } else {
      await createFresh()
    }
    buildIconStrip()
    setInterval(poll, POLL_MS)
    requestAnimationFrame(loop)
  }

  async function createFresh() {
    const data = await api.createUser()
    adopt(data)
  }

  async function poll() {
    if (!userId || busy) return
    try {
      const data = await api.getPet(userId)
      setView(data.pet)
    } catch {
      /* transient; try again next tick */
    }
  }

  // ---- render loop -----------------------------------------------------
  function loop() {
    const nowMs = performance.now()
    renderer.draw(view, { mode, dark: getDark(), eggElapsed: eggElapsed() }, nowMs)

    // Trigger the server-side hatch once the local animation completes.
    if (view && view.species === 'egg' && eggElapsed() >= 60 && !hatchRequested) {
      hatchRequested = true
      hatch()
    }
    requestAnimationFrame(loop)
  }

  async function hatch() {
    try {
      const data = await api.hatch(userId)
      setView(data.pet)
      if (data.pet.species !== 'egg') {
        toast(`It hatched! Meet your ${data.pet.species}! 🎉`)
      }
    } catch {
      hatchRequested = false // allow a retry on the next frame
    }
  }

  // ---- 3-button controls ----------------------------------------------
  function move() {
    if (mode !== 'main') {
      mode = 'main'
      return
    }
    selected = (selected + 1) % ICONS.length
    paintSelection()
  }

  async function select() {
    if (mode === 'status') {
      mode = 'main'
      return
    }
    const icon = ICONS[selected]
    if (icon.action === '__status__') {
      mode = 'status'
      return
    }
    if (!userId || busy) return
    busy = true
    try {
      const data = await api.action(userId, icon.action)
      setView(data.pet)
      if (icon.id === 'light') toast(data.pet.lights_off ? 'Lights off 🌙' : 'Lights on ☀️')
    } catch (err) {
      toast(err.message || 'Hmm, that didn’t work')
    } finally {
      busy = false
    }
  }

  function cancel() {
    mode = 'main'
  }

  function button(which) {
    if (which === 'A') move()
    else if (which === 'B') select()
    else if (which === 'C') cancel()
  }

  // ---- external actions (drawer) --------------------------------------
  async function reset() {
    if (!userId) return
    const data = await api.reset(userId)
    setView(data.pet)
    mode = 'main'
    selected = 0
    paintSelection()
    toast('A fresh egg! 🥚')
  }

  async function recover(code) {
    const data = await api.recover(code)
    userId = data.user_id
    store.adoptUser(data.user_id, data.recovery_code)
    setView(data.pet)
    mode = 'main'
    toast('Pet restored! 🐣')
    return data
  }

  return {
    start,
    button,
    reset,
    recover,
    getRecoveryCode: () => store.getRecoveryCode(),
  }
}
