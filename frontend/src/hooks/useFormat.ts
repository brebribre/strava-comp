/** Display formatting. Kept out of containers so templates stay declarative. */
export function useFormat() {
  function km(metres: number): string {
    return `${(metres / 1000).toFixed(1)} km`
  }

  function duration(seconds: number): string {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.round((seconds % 3600) / 60)
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
  }

  function elevation(metres: number): string {
    return `${Math.round(metres)} m`
  }

  function heartrate(bpm: number | null): string {
    return bpm === null ? '—' : `${Math.round(bpm)} bpm`
  }

  function shortDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }

  /**
   * A calendar date that must not shift with the viewer's timezone.
   *
   * Target end dates are stored as 23:59:59Z, which renders as the *next* day for anyone
   * east of UTC — so these are formatted in UTC deliberately.
   */
  function utcDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, {
      timeZone: 'UTC',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  function time(iso: string): string {
    return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  }

  function initials(name: string): string {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]!.toUpperCase())
      .join('')
  }

  // Strava reports a distance for court sports too, but "min/km" is meaningless there —
  // only foot sports get a pace, and wheels get a speed.
  const FOOT_SPORTS = new Set(['Run', 'TrailRun', 'VirtualRun', 'Walk', 'Hike'])
  const WHEEL_SPORTS = new Set(['Ride', 'VirtualRide', 'GravelRide', 'MountainBikeRide', 'EBikeRide'])

  /** Pace (foot sports) or average speed (cycling); null when neither applies. */
  function paceOrSpeed(
    sportType: string | null,
    metres: number,
    seconds: number,
  ): { label: string; value: string } | null {
    if (!sportType || metres < 100 || seconds <= 0) return null

    if (FOOT_SPORTS.has(sportType)) {
      // Round the total first: rounding the seconds separately produces "6:60 /km".
      const total = Math.round(seconds / (metres / 1000))
      const minutes = Math.floor(total / 60)
      const rest = total % 60
      return { label: 'Pace', value: `${minutes}:${String(rest).padStart(2, '0')} /km` }
    }

    if (WHEEL_SPORTS.has(sportType)) {
      return { label: 'Speed', value: `${((metres / 1000 / seconds) * 3600).toFixed(1)} km/h` }
    }

    return null
  }

  /** Seconds per km as m:ss — used by the recap, where pace is already aggregated. */
  function pace(secondsPerKm: number | null): string {
    if (!secondsPerKm) return '—'
    const total = Math.round(secondsPerKm)
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')} /km`
  }

  /** The exercises of a gym session as one line, each name once, in the order done. */
  function exerciseSummary(exercises: { name: string }[]): string {
    const seen = new Set<string>()
    return exercises
      .map((exercise) => exercise.name)
      .filter((name) => !seen.has(name) && seen.add(name))
      .join(' · ')
  }

  /** "Bryan Alvin" → "Bryan". Greeting-style, for the phone's profile bar. */
  function firstName(name: string): string {
    return name.trim().split(/\s+/)[0] ?? name
  }

  /** Strava sport types are PascalCase: "WeightTraining" reads as "Weight Training". */
  function sportLabel(sportType: string): string {
    return sportType.replace(/([a-z\d])([A-Z])/g, '$1 $2')
  }

  return {
    km, duration, elevation, heartrate, shortDate, utcDate, time, initials, paceOrSpeed, pace,
    sportLabel, firstName, exerciseSummary,
  }
}
