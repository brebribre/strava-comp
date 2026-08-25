import { computed } from 'vue'

/**
 * Chart palette.
 *
 * Charts render to canvas, so they can't read CSS variables — the values are resolved here
 * instead. The app is dark-only, so there's one ramp: with no hue to separate series,
 * stacked segments are distinguished by lightness, spaced far enough apart to stay legible
 * next to each other.
 */
const RAMP = ['#fafafa', '#cfcfcf', '#a3a3a3', '#7a7a7a', '#555555', '#3a3a3a']

// Grid, ticks and legend text, matching --color-ink-muted and --color-line.
const CHART_INK = '#a3a3a3'
const CHART_GRID = '#2c3a37'

export function useSportColors() {
  /**
   * Tone is assigned by position in the sorted list of sports present, not hashed — a hash
   * would scatter adjacent stack segments onto near-identical greys.
   */
  function colorForIndex(index: number): string {
    return RAMP[index % RAMP.length]
  }

  function colorFor(sport: string, all: string[] = []): string {
    const index = all.indexOf(sport)
    return colorForIndex(index >= 0 ? index : 0)
  }

  const chartInk = computed(() => CHART_INK)
  const chartGrid = computed(() => CHART_GRID)

  return { colorFor, colorForIndex, chartInk, chartGrid }
}
