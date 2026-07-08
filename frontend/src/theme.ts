/**
 * Design tokens -- single source of truth for raw hex values consumed by SVG/canvas
 * surfaces (charts, the Leaflet map) that can't use Tailwind utility classes. General UI
 * chrome uses the matching Tailwind tokens defined in index.css's @theme block; keep the
 * two in sync by hand when either changes.
 *
 * Categorical theme-color assignment is FIXED (never derived from array index / cycled) --
 * required so a filtered/reordered list never repaints a theme's color, and chosen for
 * semantic fit rather than palette row order. "other" gets a muted neutral rather than a
 * vivid slot since it's a catch-all, not a real fixed identity.
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
  water: { fg: '#0d3f73', bg: '#dbeafe', fgDark: '#bcd9f7', bgDark: '#153352', swatch: '#2a78d6', swatchDark: '#3987e5' },
  sanitation: { fg: '#0b5a3f', bg: '#d6f3e8', fgDark: '#a9e8cf', bgDark: '#0f3d2c', swatch: '#1baf7a', swatchDark: '#199e70' },
  electricity: { fg: '#7a5200', bg: '#fdedcc', fgDark: '#f2cb7d', bgDark: '#4a3800', swatch: '#eda100', swatchDark: '#c98500' },
  school: { fg: '#332875', bg: '#e7e3fb', fgDark: '#cac2f2', bgDark: '#251d54', swatch: '#4a3aa7', swatchDark: '#9085e9' },
  road: { fg: '#7a2e10', bg: '#fbe2d3', fgDark: '#f2b48f', bgDark: '#4a2211', swatch: '#eb6834', swatchDark: '#d95926' },
  health: { fg: '#7a2249', bg: '#fbdfeb', fgDark: '#f0a8c8', bgDark: '#4a1730', swatch: '#e87ba4', swatchDark: '#d55181' },
  other: { fg: '#4b4a46', bg: '#eeede8', fgDark: '#c3c2b7', bgDark: '#2c2c2a', swatch: '#898781', swatchDark: '#898781' },
}

export function themeColor(theme: string): ThemeColor {
  return THEME_COLORS[theme] ?? THEME_COLORS.other
}

// Reserved, never reused for a category -- always paired with an icon + label, never color
// alone (warning/serious drop under 3:1 contrast on the light surface by design).
export const STATUS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
} as const

// Chart chrome -- matches references/palette.md exactly.
export const CHART = {
  light: {
    surface: '#fcfcfb',
    plane: '#f9f9f7',
    textPrimary: '#0b0b0b',
    textSecondary: '#52514e',
    textMuted: '#898781',
    gridline: '#e1e0d9',
    axis: '#c3c2b7',
  },
  dark: {
    surface: '#1a1a19',
    plane: '#0d0d0d',
    textPrimary: '#ffffff',
    textSecondary: '#c3c2b7',
    textMuted: '#898781',
    gridline: '#2c2c2a',
    axis: '#383835',
  },
}

// Single-hue sequential ramp (blue), for magnitude fills like meters/gauges.
export const SEQUENTIAL_BLUE = {
  100: '#cde2fb',
  200: '#9ec5f4',
  300: '#6da7ec',
  400: '#3987e5',
  500: '#256abf',
  600: '#184f95',
  700: '#0d366b',
}

export function scoreStatus(score: number): 'good' | 'warning' | 'critical' {
  if (score >= 0.7) return 'critical' // highest-priority need -- most urgent to act on
  if (score >= 0.4) return 'warning'
  return 'good'
}
