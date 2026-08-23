export interface Point {
  lat: number
  lng: number
}

/**
 * Decode Google's encoded-polyline format, which is what Strava returns for activity maps.
 *
 * Values are stored as deltas, zig-zag encoded into 5-bit chunks with a continuation bit.
 * https://developers.google.com/maps/documentation/utilities/polylinealgorithm
 */
export function decodePolyline(encoded: string): Point[] {
  const points: Point[] = []
  let index = 0
  let lat = 0
  let lng = 0

  while (index < encoded.length) {
    for (const axis of ['lat', 'lng'] as const) {
      let result = 0
      let shift = 0
      let byte: number

      do {
        byte = encoded.charCodeAt(index++) - 63
        result |= (byte & 0x1f) << shift
        shift += 5
      } while (byte >= 0x20)

      // Least-significant bit set means the value was negative before zig-zagging.
      const delta = result & 1 ? ~(result >> 1) : result >> 1
      if (axis === 'lat') lat += delta
      else lng += delta
    }
    points.push({ lat: lat / 1e5, lng: lng / 1e5 })
  }

  return points
}

/** Project decoded points into an SVG viewBox, preserving aspect ratio. */
export function usePolyline() {
  function toSvgPath(encoded: string | null, width = 600, height = 320, padding = 12): string | null {
    if (!encoded) return null
    const points = decodePolyline(encoded)
    if (points.length < 2) return null

    const lats = points.map((p) => p.lat)
    const lngs = points.map((p) => p.lng)
    const minLat = Math.min(...lats)
    const maxLat = Math.max(...lats)
    const minLng = Math.min(...lngs)
    const maxLng = Math.max(...lngs)

    // Longitude degrees shrink with latitude, so scale x by cos(lat) or the shape skews.
    const midLat = ((minLat + maxLat) / 2) * (Math.PI / 180)
    const spanX = Math.max((maxLng - minLng) * Math.cos(midLat), 1e-9)
    const spanY = Math.max(maxLat - minLat, 1e-9)

    // One scale for both axes keeps the route's true proportions.
    const scale = Math.min((width - padding * 2) / spanX, (height - padding * 2) / spanY)
    const offsetX = (width - spanX * scale) / 2
    const offsetY = (height - spanY * scale) / 2

    return points
      .map((point, index) => {
        const x = (point.lng - minLng) * Math.cos(midLat) * scale + offsetX
        // SVG y grows downward; latitude grows upward.
        const y = height - ((point.lat - minLat) * scale + offsetY)
        return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }

  return { toSvgPath }
}
