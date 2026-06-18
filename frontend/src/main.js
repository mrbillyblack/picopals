import './style.css'
import { createGame } from './game.js'
import { store } from './store.js'
import { COLORS } from './config.js'

// ---------------------------------------------------------------------------
// Element refs
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel)

const deviceEl = $('#device')
const canvas = $('#lcd')
const topRow = document.querySelector('.iconrow--top')
const bottomRow = document.querySelector('.iconrow--bottom')
const toastEl = $('#toast')

// ---------------------------------------------------------------------------
// Theme + device color
// ---------------------------------------------------------------------------
let settings = store.getSettings()

function applyTheme() {
  document.documentElement.dataset.theme = settings.dark ? 'dark' : 'light'
  deviceEl.dataset.color = settings.color
  $('#toggle-dark').checked = settings.dark
  document
    .querySelectorAll('#color-swatches .swatch')
    .forEach((s) => s.classList.toggle('swatch--active', s.dataset.color === settings.color))
}

function buildSwatches() {
  const wrap = $('#color-swatches')
  wrap.innerHTML = ''
  COLORS.forEach((c) => {
    const b = document.createElement('button')
    b.className = 'swatch'
    b.dataset.color = c.id
    b.title = c.label
    b.addEventListener('click', () => {
      settings = store.setSettings({ color: c.id })
      applyTheme()
    })
    wrap.appendChild(b)
  })
}

$('#toggle-dark').addEventListener('change', (e) => {
  settings = store.setSettings({ dark: e.target.checked })
  applyTheme()
})

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
let toastTimer
function toast(msg) {
  toastEl.textContent = msg
  toastEl.hidden = false
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toastEl.hidden = true), 2600)
}

// ---------------------------------------------------------------------------
// Game
// ---------------------------------------------------------------------------
const game = createGame({
  canvas,
  topRow,
  bottomRow,
  getDark: () => settings.dark,
  toast,
})

// Hardware buttons
document.querySelectorAll('.hwbtn').forEach((btn) => {
  btn.addEventListener('click', () => game.button(btn.dataset.btn))
})

// Keyboard: A/B/C or arrows + space
window.addEventListener('keydown', (e) => {
  if (e.target.matches('input, textarea')) return
  const map = {
    a: 'A', arrowleft: 'A',
    b: 'B', ' ': 'B', enter: 'B',
    c: 'C', arrowright: 'C', escape: 'C',
  }
  const which = map[e.key.toLowerCase()]
  if (which) {
    e.preventDefault()
    game.button(which)
  }
})

// ---------------------------------------------------------------------------
// Drawer
// ---------------------------------------------------------------------------
const drawer = $('#drawer')
const scrim = $('#drawer-scrim')
const panels = ['settings', 'about', 'reset']

function openDrawer() {
  drawer.hidden = false
  scrim.hidden = false
  // Refresh the recovery code each time it's opened.
  $('#recovery-code').textContent = game.getRecoveryCode() || '…'
}
function closeDrawer() {
  drawer.hidden = true
  scrim.hidden = true
  showPanel(null)
}
function showPanel(name) {
  panels.forEach((p) => ($(`#panel-${p}`).hidden = p !== name))
}

$('#hamburger').addEventListener('click', openDrawer)
scrim.addEventListener('click', closeDrawer)
document.querySelectorAll('.drawer__item').forEach((item) => {
  item.addEventListener('click', () => showPanel(item.dataset.panel))
})

// Reset flow
$('#reset-confirm').addEventListener('click', async () => {
  await game.reset()
  closeDrawer()
})
$('#reset-cancel').addEventListener('click', () => showPanel(null))

// Recover flow
$('#recover-btn').addEventListener('click', async () => {
  const code = $('#recover-input').value.trim()
  const msg = $('#recover-msg')
  if (!code) return
  try {
    await game.recover(code)
    msg.textContent = 'Restored!'
    msg.className = 'msg msg--ok'
    $('#recovery-code').textContent = game.getRecoveryCode()
    setTimeout(closeDrawer, 800)
  } catch (err) {
    msg.textContent = err.status === 404 ? 'No pet found for that code.' : 'Could not restore.'
    msg.className = 'msg msg--err'
  }
})

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
buildSwatches()
applyTheme()

game.start().catch((err) => {
  console.error(err)
  toast('Could not reach the server. Is the backend running?')
})

// PWA service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
