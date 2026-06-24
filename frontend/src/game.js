import { api } from './api.js'
import { store } from './store.js'
import { createRenderer } from './render.js'
import { POLL_MS, HATCH_SECONDS } from './config.js'

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

export function createGame({ canvas, nameInput, topRow, bottomRow, getDark, toast }) {
  const renderer = createRenderer(canvas)

  let view = null
  let userId = null
  let clockOffset = 0 // serverTime - localTime (seconds)
  let mode = 'main' // 'main' | 'status'
  let selected = 0
  let lastHatchAt = 0 // performance.now() of the last hatch attempt (debounce)
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
    bindNameInput()
    setInterval(poll, POLL_MS)
    requestAnimationFrame(loop)
  }

  function bindNameInput() {
    // Commit on blur / Enter; the loop repopulates from server state afterwards.
    nameInput.addEventListener('change', () => setName(nameInput.value.trim()))
    nameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault()
        nameInput.blur()
      }
    })
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

    // Pet-name editor overlay: only on the Stats screen for a hatched pet.
    // Don't clobber what the user is typing (skip while it has focus).
    const showName = mode === 'status' && !!view && view.species !== 'egg'
    nameInput.hidden = !showName
    if (showName && document.activeElement !== nameInput) {
      nameInput.value = view.name || ''
      nameInput.placeholder = view.species.toUpperCase()
    }

    // Once the local animation completes, ask the server to hatch. Retry on a
    // ~1.2s debounce (not every frame) until the species actually changes, so a
    // borderline "not ready yet" response or a transient error can't leave the
    // egg stuck strobing the hatch flash forever.
    if (view && view.species === 'egg' && eggElapsed() >= HATCH_SECONDS &&
        nowMs - lastHatchAt > 1200) {
      lastHatchAt = nowMs
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
      /* transient — the loop retries on the next debounced tick */
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

  async function setName(name) {
    if (!userId) return
    const data = await api.setName(userId, name)
    setView(data.pet)
    return data.pet
  }

  return {
    start,
    button,
    reset,
    recover,
    setName,
    getName: () => (view && view.name ? view.name : ''),
    getRecoveryCode: () => store.getRecoveryCode(),
  }
}
