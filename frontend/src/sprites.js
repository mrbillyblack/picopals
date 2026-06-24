// Monochrome LCD pixel art. To guarantee symmetry (and to avoid off-by-one
// counting bugs), each creature is authored as sixteen 8-pixel *left halves*;
// mirror() reflects them into full 16x16 grids. '1' = a dark LCD pixel.
//
// All four animals share a body whose eyes sit at column 4 / row 7 (mirrored to
// column 11), so a single blink animation works for every species.

function mirror(left) {
  return left.map((row) => row + [...row].reverse().join(''))
}

// Shared lower body, rows 4..15.
const BODY = [
  '...11111', // 4
  '..111111', // 5
  '.1100111', // 6  <- eyes, upper (2x2 blocks: cols 3-4, mirrored to 11-12)
  '.1100111', // 7  <- eyes, lower
  '.1111111', // 8
  '.1111111', // 9
  '.1111011', // 10 <- smile: corners turn up (cols 5 / 10)
  '.1111100', // 11 <- smile: wide bottom (cols 6-9)
  '..111111', // 12
  '..111111', // 13
  '..111111', // 14
  '..11....', // 15 <- two feet
]

const DOG_TOP = ['........', '.11.....', '.111....', '.111....'] // floppy ears
const CAT_TOP = ['..1.....', '..11....', '.111....', '.1111...'] // pointed ears
const RABBIT_TOP = ['....11..', '....11..', '....11..', '...1111.'] // tall ears

const EGG_IDLE_L = [
  '......11', '.....111', '....1111', '....1111',
  '...11111', '...11111', '..111111', '..111111',
  '..111111', '..111111', '...11111', '...11111',
  '....1111', '....1111', '.....111', '......11',
]

// Same silhouette as the egg but with a jagged central crack.
const EGG_CRACK_L = [
  '......11', '.....111', '....1111', '....1111',
  '...11111', '...11110', '..111101', '..111110',
  '..111101', '..111110', '...11111', '...11111',
  '....1111', '....1111', '.....111', '......11',
]

// Frog is squatter and wider, so it gets a full bespoke set.
const FROG_L = [
  '........', '...11...', '..1111..', '.111111.',
  '11111111', '11111111', '11100111', '11100111', // eyes (2x2, cols 3-4)
  '11111111', '11111111', '11110111', '11111000', // "c:" grin (corners up, wide bottom)
  '11111111', '.1111111', '11111111', '11..11..', // webbed feet
]

const POOP = ['...11...', '..1111..', '.111111.', '11111111']

// The cells covering each eye, so the blink overlay can close them.
export const EYES = [
  [3, 6], [4, 6], [3, 7], [4, 7], // left eye (2x2)
  [11, 6], [12, 6], [11, 7], [12, 7], // right eye (2x2)
]

export const SPRITES = {
  egg: { grid: mirror(EGG_IDLE_L), eyes: null },
  egg_crack: { grid: mirror(EGG_CRACK_L), eyes: null },
  dog: { grid: mirror([...DOG_TOP, ...BODY]), eyes: EYES },
  cat: { grid: mirror([...CAT_TOP, ...BODY]), eyes: EYES },
  rabbit: { grid: mirror([...RABBIT_TOP, ...BODY]), eyes: EYES },
  frog: { grid: mirror(FROG_L), eyes: EYES },
  poop: { grid: POOP, eyes: null },
}

export const GRID = 16
