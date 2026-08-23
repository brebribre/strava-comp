import { ref } from 'vue'

import { useFormat } from '@/hooks/useFormat'
import { useSportIcon } from '@/hooks/useSportIcon'
import type { ActivityDetail } from '@/types/api'

// Portrait 4:5 — the shape chat apps and stories show without cropping.
const WIDTH = 1080
const HEIGHT = 1350
const PAD = 84

// The card is always dark, regardless of the viewer's theme: it gets sent into other
// people's chats, where it should look deliberate rather than inherit our page state.
const INK = '#fafafa'
const INK_MUTED = '#8f8f8f'
const CANVAS_BG = '#0a0a0a'
const LINE = '#2a2a2a'

const FONT = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

/** Renders an activity as a shareable PNG and hands it to the OS share sheet or a download. */
export function useShareCard() {
  const { km, duration, elevation, heartrate, initials, paceOrSpeed } = useFormat()
  const { geometry } = useSportIcon()

  const isWorking = ref(false)
  const error = ref<string | null>(null)
  const previewUrl = ref<string | null>(null)

  function statsFor(activity: ActivityDetail): { label: string; value: string }[] {
    const stats: { label: string; value: string }[] = []
    if (activity.distance > 0) stats.push({ label: 'Distance', value: km(activity.distance) })
    stats.push({ label: 'Moving time', value: duration(activity.moving_time) })
    const rate = paceOrSpeed(activity.sport_type, activity.distance, activity.moving_time)
    if (rate) stats.push(rate)
    if (activity.total_elevation_gain > 0) {
      stats.push({ label: 'Elevation', value: elevation(activity.total_elevation_gain) })
    }
    if (activity.average_heartrate !== null) {
      stats.push({ label: 'Avg HR', value: heartrate(activity.average_heartrate) })
    }
    if (activity.max_heartrate !== null) {
      stats.push({ label: 'Max HR', value: heartrate(activity.max_heartrate) })
    }
    if (activity.calories !== null) {
      stats.push({ label: 'Calories', value: `${Math.round(activity.calories)}` })
    }
    return stats
  }

  function drawIcon(
    ctx: CanvasRenderingContext2D,
    sportType: string | null,
    x: number,
    y: number,
    size: number,
  ) {
    const { paths, circles, rects, ellipses } = geometry(sportType)
    const scale = size / 48

    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    ctx.strokeStyle = INK
    ctx.lineWidth = 2.6
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    for (const d of paths) ctx.stroke(new Path2D(d))
    for (const [cx, cy, r] of circles) {
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.stroke()
    }
    for (const [rx, ry, w, h, radius] of rects) {
      ctx.beginPath()
      ctx.roundRect(rx, ry, w, h, radius)
      ctx.stroke()
    }
    for (const [cx, cy, rx, ry, rotation] of ellipses) {
      ctx.beginPath()
      ctx.ellipse(cx, cy, rx, ry, (rotation * Math.PI) / 180, 0, Math.PI * 2)
      ctx.stroke()
    }
    ctx.restore()
  }

  function drawAvatar(ctx: CanvasRenderingContext2D, name: string, x: number, y: number, size: number) {
    ctx.save()
    ctx.strokeStyle = LINE
    ctx.fillStyle = '#181818'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.roundRect(x, y, size, size, 12)
    ctx.fill()
    ctx.stroke()

    ctx.fillStyle = INK_MUTED
    ctx.font = `600 ${Math.round(size * 0.36)}px ${FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(initials(name), x + size / 2, y + size / 2 + 2)
    ctx.restore()
  }

  function render(activity: ActivityDetail): HTMLCanvasElement {
    const canvas = document.createElement('canvas')
    canvas.width = WIDTH
    canvas.height = HEIGHT
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas unsupported')

    ctx.fillStyle = CANVAS_BG
    ctx.fillRect(0, 0, WIDTH, HEIGHT)

    // ── Profile row ──────────────────────────────────────────────────────────
    const avatarSize = 96
    drawAvatar(ctx, activity.athlete_name, PAD, PAD, avatarSize)

    ctx.textAlign = 'left'
    ctx.textBaseline = 'alphabetic'
    ctx.fillStyle = INK
    ctx.font = `600 40px ${FONT}`
    ctx.fillText(activity.athlete_name, PAD + avatarSize + 28, PAD + 42)

    ctx.fillStyle = INK_MUTED
    ctx.font = `400 30px ${FONT}`
    const when = new Date(activity.start_date).toLocaleString(undefined, {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
    ctx.fillText(when, PAD + avatarSize + 28, PAD + 86)

    // ── Sport icon + title ───────────────────────────────────────────────────
    const iconTop = PAD + 210
    drawIcon(ctx, activity.sport_type, PAD, iconTop, 130)

    ctx.fillStyle = INK_MUTED
    ctx.font = `500 30px ${FONT}`
    ctx.fillText((activity.sport_type ?? 'Activity').toUpperCase(), PAD, iconTop + 200)

    ctx.fillStyle = INK
    ctx.font = `700 66px ${FONT}`
    const title = activity.name ?? 'Untitled activity'
    // Two lines maximum, ellipsised — long titles must not push the stats off the card.
    const words = title.split(' ')
    const lines: string[] = []
    let line = ''
    for (const word of words) {
      const candidate = line ? `${line} ${word}` : word
      if (ctx.measureText(candidate).width > WIDTH - PAD * 2 && line) {
        lines.push(line)
        line = word
      } else {
        line = candidate
      }
      if (lines.length === 2) break
    }
    if (lines.length < 2 && line) lines.push(line)
    lines.slice(0, 2).forEach((text, index) => {
      const isLast = index === 1 && words.join(' ') !== lines.join(' ')
      ctx.fillText(isLast ? `${text}…` : text, PAD, iconTop + 280 + index * 78)
    })

    // ── Stats grid ───────────────────────────────────────────────────────────
    const stats = statsFor(activity)
    const gridTop = iconTop + 400
    const colWidth = (WIDTH - PAD * 2) / 2
    stats.slice(0, 6).forEach((stat, index) => {
      const col = index % 2
      const row = Math.floor(index / 2)
      const x = PAD + col * colWidth
      const y = gridTop + row * 150

      ctx.fillStyle = INK_MUTED
      ctx.font = `500 28px ${FONT}`
      ctx.fillText(stat.label.toUpperCase(), x, y)

      ctx.fillStyle = INK
      ctx.font = `700 58px ${FONT}`
      ctx.fillText(stat.value, x, y + 66)
    })

    // ── Footer ───────────────────────────────────────────────────────────────
    ctx.strokeStyle = LINE
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(PAD, HEIGHT - PAD - 70)
    ctx.lineTo(WIDTH - PAD, HEIGHT - PAD - 70)
    ctx.stroke()

    ctx.fillStyle = INK_MUTED
    ctx.font = `500 28px ${FONT}`
    ctx.fillText('bruderbande.com', PAD, HEIGHT - PAD - 14)

    return canvas
  }

  function toBlob(canvas: HTMLCanvasElement): Promise<Blob> {
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('could not encode the image'))),
        'image/png',
      )
    })
  }

  /** Build the card and show it. Revokes the previous object URL so blobs don't pile up. */
  async function preview(activity: ActivityDetail) {
    isWorking.value = true
    error.value = null
    try {
      const blob = await toBlob(render(activity))
      if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = URL.createObjectURL(blob)
      return blob
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Could not build the image'
      return null
    } finally {
      isWorking.value = false
    }
  }

  function clear() {
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
    error.value = null
  }

  function fileName(activity: ActivityDetail): string {
    const date = new Date(activity.start_date).toISOString().slice(0, 10)
    const slug = (activity.name ?? 'activity').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)
    return `${date}-${slug}.png`.replace(/-+\./, '.')
  }

  /** True when the OS share sheet can take a file — the path that reaches WhatsApp. */
  function canShareFiles(activity: ActivityDetail): boolean {
    if (typeof navigator === 'undefined' || !navigator.canShare) return false
    const probe = new File([new Blob()], fileName(activity), { type: 'image/png' })
    return navigator.canShare({ files: [probe] })
  }

  async function share(activity: ActivityDetail) {
    const blob = await preview(activity)
    if (!blob) return false
    const file = new File([blob], fileName(activity), { type: 'image/png' })
    try {
      await navigator.share({ files: [file], title: activity.name ?? 'Activity' })
      return true
    } catch {
      // Includes the user simply dismissing the share sheet — not worth an error message.
      return false
    }
  }

  function download(activity: ActivityDetail) {
    if (!previewUrl.value) return
    const link = document.createElement('a')
    link.href = previewUrl.value
    link.download = fileName(activity)
    link.click()
  }

  return { preview, share, download, clear, canShareFiles, previewUrl, isWorking, error }
}
