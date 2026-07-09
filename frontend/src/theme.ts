/**
 * Design tokens -- single source of truth for raw hex values consumed by SVG/canvas
 * surfaces (charts, the Leaflet map) that can't use Tailwind utility classes. General UI
 * chrome uses the matching Tailwind tokens defined in index.css's @theme block; keep the
 * two in sync by hand when either changes.
 *
 * Categorical theme-color assignment is FIXED (never derived from array index / cycled) --
 * required so a filtered/reordered list never repaints a theme's color, and chosen for
 * semantic fit rather than palette row order. "other" gets a muted neutral rather than a
 * vivid slot since it's a catch-all, not a real fixed identity. Hues are spread across the
 * wheel as a mineral/pigment set (teal, jade, mustard, plum, rust, berry, stone) so no
 * category is mistaken for the accent (indigo) or the good/warning/critical semantic trio.
 */

export interface ThemeColor {
  fg: string // text/icon on a light chip
  bg: string // light chip background
  fgDark: string
  bgDark: string
  swatch: string // solid hue, for map markers / chart bars
  swatchDark: string
}

export const THEME_COLORS: Record<string, ThemeColor> = {
  water: { fg: '#0d3846', bg: '#dcebef', fgDark: '#bfe1ea', bgDark: '#16323c', swatch: '#1f6e86', swatchDark: '#4fa6c2' },
  sanitation: { fg: '#0c3f2c', bg: '#dceee6', fgDark: '#b9e6d2', bgDark: '#143a2c', swatch: '#1f7a5c', swatchDark: '#4fbe95' },
  electricity: { fg: '#4a3a0d', bg: '#efe7d0', fgDark: '#e6d6a0', bgDark: '#3a2e10', swatch: '#8a6d1e', swatchDark: '#c7a94e' },
  school: { fg: '#2e2450', bg: '#e5e1f1', fgDark: '#cdc4ea', bgDark: '#29224a', swatch: '#5b4a8c', swatchDark: '#9284c4' },
  road: { fg: '#5c2a12', bg: '#f3dfd1', fgDark: '#f0c4a8', bgDark: '#452213', swatch: '#b0562b', swatchDark: '#e0895a' },
  health: { fg: '#4a1830', bg: '#f0dce6', fgDark: '#efc0d6', bgDark: '#3e1729', swatch: '#93395e', swatchDark: '#cc6e97' },
  other: { fg: '#3f3b30', bg: '#eae7de', fgDark: '#d6d1c1', bgDark: '#322f26', swatch: '#7a7462', swatchDark: '#aca690' },
}

export function themeColor(theme: string): ThemeColor {
  return THEME_COLORS[theme] ?? THEME_COLORS.other
}

// Reserved, never reused for a category -- always paired with an icon + label, never color
// alone (warning/serious drop under 3:1 contrast on the light surface by design).
export const STATUS = {
  good: '#3e7a49',
  warning: '#b9701c',
  critical: '#b23a2e',
} as const

export function scoreStatus(score: number): 'good' | 'warning' | 'critical' {
  if (score >= 0.7) return 'critical' // highest-priority need -- most urgent to act on
  if (score >= 0.4) return 'warning'
  return 'good'
}
