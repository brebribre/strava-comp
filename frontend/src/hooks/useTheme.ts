import { computed, watch } from 'vue'

import { useThemeStore, type TintLevel } from '@/stores/useThemeStore'

const STORAGE_KEY = 'bruderbande.accent'
const TINT_KEY = 'bruderbande.tint'

/**
 * How much accent bleeds into backgrounds, per surface.
 *
 * Cards get slightly more than the page and lines more still, so the existing depth
 * ordering survives the tint instead of flattening into one wash.
 */
const TINT_LEVELS: Record<TintLevel, { canvas: string; surface: string; raised: string; line: string }> = {
  none: { canvas: '0%', surface: '0%', raised: '0%', line: '0%' },
  subtle: { canvas: '5%', surface: '6%', raised: '9%', line: '14%' },
  strong: { canvas: '12%', surface: '14%', raised: '20%', line: '28%' },
}

export const TINT_OPTIONS: { value: TintLevel; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'subtle', label: 'Subtle' },
  { value: 'strong', label: 'Strong' },
]

export interface AccentPreset {
  name: string
  value: string | null
}

/** Deliberately muted: these sit on a near-black or near-white page, not on a brand site. */
export const ACCENT_PRESETS: AccentPreset[] = [
  { name: 'Monochrome', value: null },
  { name: 'Ember', value: '#fc4c02' },
  { name: 'Rust', value: '#c2410c' },
  { name: 'Amber', value: '#d97706' },
  { name: 'Moss', value: '#4d7c0f' },
  { name: 'Pine', value: '#047857' },
  { name: 'Teal', value: '#0f766e' },
  { name: 'Ocean', value: '#0369a1' },
  { name: 'Indigo', value: '#4338ca' },
  { name: 'Violet', value: '#6d28d9' },
  { name: 'Plum', value: '#a21caf' },
  { name: 'Crimson', value: '#be123c' },
]

function parseHex(hex: string): [number, number, number] | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!match) return null
  const value = parseInt(match[1], 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

/**
 * Relative luminance per WCAG, used to decide whether text on the accent should be black
 * or white. Picking one by eye breaks as soon as someone chooses yellow.
 */
function luminance([r, g, b]: [number, number, number]): number {
  const channel = (value: number) => {
    const c = value / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

export function useTheme() {
  const store = useThemeStore()

  const accent = computed(() => store.accent)
  const isMonochrome = computed(() => store.accent === null)

  function isValid(hex: string): boolean {
    return parseHex(hex) !== null
  }

  function apply(value: string | null, tint: TintLevel = store.tint) {
    const root = document.documentElement
    // Backgrounds are only tinted when there's a colour to tint them with.
    const amounts = value ? TINT_LEVELS[tint] : TINT_LEVELS.none
    root.style.setProperty('--tint-canvas', amounts.canvas)
    root.style.setProperty('--tint-surface', amounts.surface)
    root.style.setProperty('--tint-raised', amounts.raised)
    root.style.setProperty('--tint-line', amounts.line)

    if (!value) {
      // Remove the overrides so the tokens fall back to ink, restoring monochrome.
      root.style.removeProperty('--color-accent')
      root.style.removeProperty('--color-accent-contrast')
      return
    }
    const rgb = parseHex(value)
    if (!rgb) return
    root.style.setProperty('--color-accent', value)
    root.style.setProperty('--color-accent-contrast', luminance(rgb) > 0.45 ? '#0a0a0a' : '#fafafa')
  }

  function set(value: string | null, tint?: TintLevel) {
    store.set(value, tint)
    apply(value, tint ?? store.tint)
    try {
      if (value) localStorage.setItem(STORAGE_KEY, value)
      else localStorage.removeItem(STORAGE_KEY)
      localStorage.setItem(TINT_KEY, store.tint)
    } catch {
      // Private modes can refuse storage; the colour still applies for this session.
    }
  }

  function setTint(tint: TintLevel) {
    set(store.accent, tint)
  }

  /** Read the saved accent and apply it. Safe to call more than once. */
  function restore() {
    if (store.isLoaded) {
      apply(store.accent)
      return
    }
    let saved: string | null = null
    try {
      saved = localStorage.getItem(STORAGE_KEY)
    } catch {
      saved = null
    }
    let savedTint: TintLevel = 'subtle'
    try {
      const raw = localStorage.getItem(TINT_KEY)
      if (raw === 'none' || raw === 'subtle' || raw === 'strong') savedTint = raw
    } catch {
      savedTint = 'subtle'
    }

    const value = saved && isValid(saved) ? saved : null
    store.set(value, savedTint)
    apply(value, savedTint)
  }

  // Keep the DOM in step if anything else changes the store.
  watch(
    () => [store.accent, store.tint] as const,
    ([value, tint]) => apply(value, tint),
  )

  const tint = computed(() => store.tint)

  return {
    accent, tint, isMonochrome,
    presets: ACCENT_PRESETS, tintOptions: TINT_OPTIONS,
    set, setTint, restore, isValid,
  }
}
