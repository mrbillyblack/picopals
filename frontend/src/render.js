// Canvas renderer for the LCD screen. Draws in a fixed 160x160 virtual space;
// CSS scales it up with image-rendering: pixelated so it stays crisp and the
// pixel-art aesthetic survives on any screen size.

import { SPRITES, GRID } from './sprites.js'
import { HATCH_SECONDS } from './config.js'

const SIZE = 160
const CELL = 8 // 16 * 8 = 128, leaving a 16px margin all around

const PALETTE = {
  light: { bg: '#c3d89b', px: '#1b2a1b', dim: '#6f7d56' },
  dark: { bg: '#0e1a0e', px: '#86e36a', dim: '#3a5a30' },
}

function drawGrid(ctx, grid, ox, oy, cell, color) {
  ctx.fillStyle = color
  for (let y = 0; y < grid.length; y++) {
    const row = grid[y]
    for (let x = 0; x < row.length; x++) {
      if (row[x] === '1') ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell)
    }
  }
}

export function createRenderer(canvas) {
  const ctx = canvas.getContext('2d')
  ctx.imageSmoothingEnabled = false

  function clear(pal) {
    ctx.fillStyle = pal.bg
    ctx.fillRect(0, 0, SIZE, SIZE)
  }

  function drawEgg(pal, eggElapsed, nowMs) {
    const phase =
      eggElapsed >= HATCH_SECONDS
        ? 'hatching'
        : eggElapsed >= HATCH_SECONDS * (2 / 3)
          ? 'cracking'
          : eggElapsed >= HATCH_SECONDS / 3
            ? 'rumbling'
            : 'idle'

    // Hatch flash: a slow, gentle pulse just before the reveal. Toggling every
    // 400ms = ~1.25 flashes/sec, well under the 3 Hz photosensitive-epilepsy
    // threshold (WCAG 2.3.1). The cracking egg stays visible underneath rather
    // than blanking to a bare screen, softening the contrast change.
    if (phase === 'hatching') {
      const ex = (SIZE - GRID * CELL) / 2
      drawGrid(ctx, SPRITES.egg_crack.grid, ex, ex, CELL, pal.px)
      if (Math.floor(nowMs / 400) % 2 === 0) {
        ctx.fillStyle = pal.px
        ctx.fillRect(0, 0, SIZE, SIZE)
      }
      return phase
    }

    let dx = 0
    if (phase === 'rumbling' || phase === 'cracking') {
      dx = Math.round(Math.sin(nowMs / 70) * (phase === 'cracking' ? 3 : 2))
    }
    const sprite = phase === 'cracking' ? SPRITES.egg_crack : SPRITES.egg
    const ox = (SIZE - GRID * CELL) / 2 + dx
    const oy = (SIZE - GRID * CELL) / 2
    drawGrid(ctx, sprite.grid, ox, oy, CELL, pal.px)
    return phase
  }

  function drawPet(pal, view, nowMs) {
    const sprite = SPRITES[view.species] || SPRITES.dog
    const bob = Math.floor(nowMs / 450) % 2 === 0 ? 0 : 1
    const ox = (SIZE - GRID * CELL) / 2
    const oy = (SIZE - GRID * CELL) / 2 + bob

    drawGrid(ctx, sprite.grid, ox, oy, CELL, pal.px)

    // Blink: fill the (light) eye holes with the body color for a beat so the
    // eyes briefly close.
    const blinking = nowMs % 4200 < 150
    if (blinking && sprite.eyes) {
      ctx.fillStyle = pal.px
      for (const [ex, ey] of sprite.eyes) {
        ctx.fillRect(ox + ex * CELL, oy + ey * CELL, CELL, CELL)
      }
    }

    // Poop piles along the bottom-left.
    for (let i = 0; i < Math.min(view.poop, 3); i++) {
      drawGrid(ctx, SPRITES.poop.grid, 6 + i * 22, SIZE - 34, 4, pal.px)
    }

    // Status glyphs.
    ctx.fillStyle = pal.px
    ctx.font = 'bold 18px ui-monospace, monospace'
    ctx.textBaseline = 'top'
    if (view.lights_off) ctx.fillText('z', SIZE - 24, 8)
    if (view.is_sick) {
      ctx.fillText('+', 10, 8)
      ctx.fillRect(8, 8, 14, 14) // a little "sick" box around the cross
      ctx.fillStyle = pal.bg
      ctx.fillText('+', 10, 8)
      ctx.fillStyle = pal.px
    }
    if (view.needs_attention && nowMs % 900 < 450) {
      ctx.fillText('!', SIZE / 2 - 4, 4)
    }
  }

  function hearts(n, max = 4) {
    const f = Math.max(0, Math.min(max, Math.round(n)))
    return '♥'.repeat(f) + '♡'.repeat(max - f)
  }

  function drawStatus(pal, view) {
    ctx.fillStyle = pal.px
    ctx.font = 'bold 13px ui-monospace, monospace'
    ctx.textBaseline = 'top'
    const lines = [
      '', // name is shown + edited via the #lcd-name HTML overlay
      '',
      'Hngr ' + hearts(view.hunger_hearts),
      'Hapy ' + hearts(view.happiness_hearts),
      'Hlth ' + hearts(view.health_hearts),
      '',
      'Age  ' + Math.floor(view.age_seconds / 60) + 'm',
      'Wt   ' + view.weight,
      'Disc ' + view.discipline,
    ]
    lines.forEach((line, i) => ctx.fillText(line, 12, 10 + i * 16))
  }

  return {
    /**
     * @param view  pet public_view from the API
     * @param ui    { mode: 'main'|'status', dark: bool, eggElapsed: number }
     * @param nowMs performance.now() timestamp
     * @returns the egg phase string when rendering an egg, else null
     */
    draw(view, ui, nowMs) {
      const pal = ui.dark ? PALETTE.dark : PALETTE.light
      clear(pal)
      if (!view) return null
      if (ui.mode === 'status' && view.species !== 'egg') {
        drawStatus(pal, view)
        return null
      }
      if (view.species === 'egg') {
        return drawEgg(pal, ui.eggElapsed, nowMs)
      }
      drawPet(pal, view, nowMs)
      return null
    },
  }
}
