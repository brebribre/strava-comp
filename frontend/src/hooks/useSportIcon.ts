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

/**
 * Sport families. Strava has dozens of `sport_type` values (TrailRun, EBikeRide, …); these
 * are the buckets everything collapses into for display purposes.
 */
export type SportFamily =
  | 'Run'
  | 'Ride'
  | 'Swim'
  | 'Tennis'
  | 'Badminton'
  | 'WeightTraining'
  | 'Walk'
  | 'Hike'
  | 'Row'
  | 'Ski'
  | 'Yoga'
  | 'Football'
  | 'Basketball'
  | 'Golf'
  | 'Workout'

export function useSportIcon() {
  /** Nearest known family for an arbitrary Strava sport_type. */
  function resolve(sportType: string | null): SportFamily {
    if (!sportType) return 'Workout'
    const lowered = sportType.toLowerCase()

    // Order matters: "TrailRun" must match run before anything else.
    if (lowered.includes('run')) return 'Run'
    if (/ride|bike|cycl/.test(lowered)) return 'Ride'
    if (lowered.includes('swim')) return 'Swim'
    if (lowered.includes('badminton')) return 'Badminton'
    if (/tennis|padel|squash|pickleball/.test(lowered)) return 'Tennis'
    if (/weight|crossfit/.test(lowered)) return 'WeightTraining'
    if (lowered.includes('hike')) return 'Hike'
    if (lowered.includes('walk')) return 'Walk'
    if (/row|kayak|canoe|paddl/.test(lowered)) return 'Row'
    if (/ski|snowboard/.test(lowered)) return 'Ski'
    if (/yoga|pilates|meditat/.test(lowered)) return 'Yoga'
    if (/soccer|football/.test(lowered)) return 'Football'
    if (lowered.includes('basketball')) return 'Basketball'
    if (lowered.includes('golf')) return 'Golf'
    return 'Workout'
  }

  function geometry(sportType: string | null): SportGeometry {
    // The hand-drawn canvas paths (share card, loader) cover fewer families than the icon
    // set does, so anything without geometry falls back to the runner.
    const family = resolve(sportType)
    const key = family in ICONS ? family : FALLBACK
    return {
      paths: ICONS[key] ?? [],
      circles: CIRCLES[key] ?? [],
      rects: RECTS[key] ?? [],
      ellipses: ELLIPSES[key] ?? [],
    }
  }

  return { resolve, geometry }
}
