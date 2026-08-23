/**
 * Sport icon geometry, as SVG path data on a 48×48 grid.
 *
 * Kept as plain path strings rather than components so the same shapes can be stroked onto
 * a canvas with Path2D for the share card, not just rendered as SVG.
 */
const ICONS: Record<string, string[]> = {
  Run: [
    'M29 14 L24 25',
    'M27 17 L35 21',
    'M27 17 L18 19',
    'M24 25 L28 34 L33 37',
    'M24 25 L17 31 L12 34',
  ],
  Ride: [
    'M11 34 L21 34 L28 21 L33 21',
    'M21 34 L29 18',
    'M37 34 L31 21',
  ],
  Swim: [
    'M9 25 L23 21 L35 24',
    'M23 21 L33 13',
    'M5 36c4 0 4-3 8-3s4 3 8 3 4-3 8-3 4 3 8 3 4-3 8-3',
  ],
  Tennis: ['M26 27 L36 39'],
  WeightTraining: ['M15 24 H33', 'M4 20 V28', 'M44 20 V28'],
  Walk: ['M28 15 L25 25', 'M25 25 L29 34', 'M25 25 L19 33', 'M26 19 L32 22'],
}

/** Circles drawn alongside the paths: [cx, cy, r]. */
const CIRCLES: Record<string, [number, number, number][]> = {
  Run: [[30, 9, 4]],
  Ride: [
    [11, 34, 7.5],
    [37, 34, 7.5],
    [31, 10, 3.5],
  ],
  Swim: [[17, 15, 4]],
  Tennis: [[38, 16, 3.5]],
  WeightTraining: [],
  Walk: [[29, 10, 4]],
}

/** Rectangles: [x, y, w, h, r]. */
const RECTS: Record<string, [number, number, number, number, number][]> = {
  WeightTraining: [
    [8, 17, 6, 14, 1.5],
    [34, 17, 6, 14, 1.5],
  ],
}

/** Ellipses: [cx, cy, rx, ry, rotationDeg]. */
const ELLIPSES: Record<string, [number, number, number, number, number][]> = {
  Tennis: [[20, 18, 10, 12, -30]],
}

const FALLBACK = 'Run'

export interface SportGeometry {
  paths: string[]
  circles: [number, number, number][]
  rects: [number, number, number, number, number][]
  ellipses: [number, number, number, number, number][]
}

export function useSportIcon() {
  /** Nearest known sport for an arbitrary Strava sport_type. */
  function resolve(sportType: string | null): string {
    if (!sportType) return FALLBACK
    if (ICONS[sportType]) return sportType
    // Strava has dozens of variants (TrailRun, VirtualRide, EBikeRide…); match the family.
    if (/run/i.test(sportType)) return 'Run'
    if (/ride|bike|cycl/i.test(sportType)) return 'Ride'
    if (/swim/i.test(sportType)) return 'Swim'
    if (/tennis|padel|squash|badminton/i.test(sportType)) return 'Tennis'
    if (/weight|workout|crossfit/i.test(sportType)) return 'WeightTraining'
    if (/walk|hike/i.test(sportType)) return 'Walk'
    return FALLBACK
  }

  function geometry(sportType: string | null): SportGeometry {
    const key = resolve(sportType)
    return {
      paths: ICONS[key] ?? [],
      circles: CIRCLES[key] ?? [],
      rects: RECTS[key] ?? [],
      ellipses: ELLIPSES[key] ?? [],
    }
  }

  return { resolve, geometry }
}
