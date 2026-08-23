import { computed } from 'vue'

/**
 * Monochrome chart palette.
 *
 * Charts render to canvas, so they can't read CSS variables or Tailwind classes — the
 * values are resolved here instead. With no hue to separate series, stacked segments are
 * distinguished by lightness, spaced far enough apart to stay legible next to each other.
 */
const LIGHT_RAMP = ['#171717', '#404040', '#666666', '#8c8c8c', '#b0b0b0', '#cfcfcf']
const DARK_RAMP = ['#fafafa', '#cfcfcf', '#a3a3a3', '#7a7a7a', '#555555', '#3a3a3a']

function prefersDark(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function useSportColors() {
  const ramp = computed(() => (prefersDark() ? DARK_RAMP : LIGHT_RAMP))

  /**
   * Tone is assigned by position in the sorted list of sports present, not hashed — a hash
   * would scatter adjacent stack segments onto near-identical greys.
   */
  function colorForIndex(index: number): string {
    return ramp.value[index % ramp.value.length]
  }

  function colorFor(sport: string, all: string[] = []): string {
    const index = all.indexOf(sport)
    return colorForIndex(index >= 0 ? index : 0)
  }

  /** Grid, ticks and legend text for Chart.js, matching the current theme. */
  const chartInk = computed(() => (prefersDark() ? '#a3a3a3' : '#525252'))
  const chartGrid = computed(() => (prefersDark() ? '#262626' : '#e5e5e5'))

  return { colorFor, colorForIndex, chartInk, chartGrid }
}
