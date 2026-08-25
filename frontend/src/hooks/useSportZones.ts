import { computed, ref, watch } from 'vue'

import { useRecapApi } from '@/api/useRecapApi'
import { ApiError } from '@/api/request'
import { useSportColors } from '@/hooks/useSportColors'
import type { ZoneRecap } from '@/types/api'

// A zone needs a few months of data before a trend line says anything...
const MIN_MONTHS_FOR_TREND = 3
// ...and enough runs overall. A zone with two or three sessions is one outlier away from
// a meaningless line that also wrecks the axis for every other zone.
const MIN_ACTIVITIES_FOR_TREND = 6

/**
 * Effort zones for one sport.
 *
 * Runs are bucketed by average heart rate rather than by workout type: Strava's
 * `workout_type` is almost never set, and interval detection needs per-split data that
 * only exists on enriched activities. Pace at a fixed effort is the cleaner signal anyway.
 */
export function useSportZones(sportType: () => string, months: () => number) {
  const api = useRecapApi()
  const { colorForIndex, chartInk, chartGrid } = useSportColors()

  const recap = ref<ZoneRecap | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const sport = sportType()
    if (!sport) return
    isLoading.value = true
    error.value = null
    try {
      recap.value = await api.zones(sport, months())
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load effort zones'
      recap.value = null
    } finally {
      isLoading.value = false
    }
  }

  const hasZones = computed(() => (recap.value?.classified_count ?? 0) > 0)

  const monthLabels = computed(() =>
    [...new Set((recap.value?.months ?? []).map((m) => m.month))].sort(),
  )

  /** One line per zone: pace over time, so improvement at a fixed effort is visible. */
  const paceChart = computed(() => {
    const points = recap.value?.months ?? []
    const labels = monthLabels.value

    const datasets = (recap.value?.zones ?? [])
      .map((zone) => {
        const forZone = points.filter((p) => p.zone === zone.zone && p.avg_pace_seconds_per_km)
        if (
          forZone.length < MIN_MONTHS_FOR_TREND ||
          zone.activity_count < MIN_ACTIVITIES_FOR_TREND
        ) {
          return null
        }
        return {
          label: `Z${zone.zone} ${zone.label}`,
          data: labels.map((month) => {
            const point = forZone.find((p) => p.month === month)
            return point?.avg_pace_seconds_per_km
              ? Math.round((point.avg_pace_seconds_per_km / 60) * 100) / 100
              : null
          }),
          borderColor: colorForIndex(zone.zone - 1),
          backgroundColor: colorForIndex(zone.zone - 1),
          tension: 0.3,
          spanGaps: true,
        }
      })
      .filter((dataset): dataset is NonNullable<typeof dataset> => dataset !== null)

    return {
      labels: labels.map((month) =>
        new Date(month).toLocaleDateString(undefined, { month: 'short', year: '2-digit' }),
      ),
      datasets,
    }
  })

  const hasTrend = computed(() => paceChart.value.datasets.length > 0)

  const paceOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: { color: chartInk.value, boxWidth: 10, boxHeight: 10, usePointStyle: true },
      },
    },
    scales: {
      x: { grid: { display: false }, border: { color: chartGrid.value }, ticks: { color: chartInk.value } },
      y: {
        // Reversed so a faster pace sits higher — improvement always points up.
        reverse: true,
        title: { display: true, text: 'Pace (min/km)', color: chartInk.value },
        grid: { color: chartGrid.value },
        border: { display: false },
        ticks: { color: chartInk.value },
      },
    },
  }))

  watch([sportType, months], refresh, { immediate: true })

  return { recap, hasZones, hasTrend, paceChart, paceOptions, isLoading, error, refresh }
}
