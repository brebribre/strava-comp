/**
 * Stable colours per sport.
 *
 * Charts render to canvas, so Tailwind classes can't reach them — these are literal values.
 * Known sports get a fixed colour so the same sport looks the same across every chart;
 * anything else is hashed into the palette rather than colliding on "first seen".
 */
const NAMED: Record<string, string> = {
  Run: '#fc4c02',
  TrailRun: '#f97316',
  Ride: '#2563eb',
  VirtualRide: '#3b82f6',
  Tennis: '#16a34a',
  WeightTraining: '#9333ea',
  Swim: '#0891b2',
  Walk: '#ca8a04',
  Hike: '#65a30d',
  Workout: '#db2777',
  Yoga: '#7c3aed',
}

const FALLBACK = ['#dc2626', '#0d9488', '#4f46e5', '#b45309', '#be185d', '#0369a1']

export function useSportColors() {
  function colorFor(sport: string): string {
    if (NAMED[sport]) return NAMED[sport]
    let hash = 0
    for (let i = 0; i < sport.length; i++) hash = (hash * 31 + sport.charCodeAt(i)) >>> 0
    return FALLBACK[hash % FALLBACK.length]
  }

  return { colorFor }
}
