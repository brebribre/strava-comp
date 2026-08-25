import { computed, ref, watch } from 'vue'

import { useRecapApi } from '@/api/useRecapApi'
import { ApiError } from '@/api/request'
import { useSportColors } from '@/hooks/useSportColors'
import type { SportRecap } from '@/types/api'

export type RecapMetric = 'distance' | 'moving_time' | 'activity_count'

export const RECAP_METRICS: { value: RecapMetric; label: string; axis: string }[] = [
  { value: 'distance', label: 'Distance', axis: 'Kilometres' },
  { value: 'moving_time', label: 'Time', axis: 'Hours' },
  { value: 'activity_count', label: 'Activities', axis: 'Activities' },
]

export function useSportRecap(sportType: () => string, months: () => number) {
  const api = useRecapApi()
  const { colorForIndex, chartInk, chartGrid } = useSportColors()

  const recap = ref<SportRecap | null>(null)
  const metric = ref<RecapMetric>('distance')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const sport = sportType()
    if (!sport) return
    isLoading.value = true
    error.value = null
    try {
      recap.value = await api.sport(sport, months())
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load this sport'
      recap.value = null
    } finally {
      isLoading.value = false
    }
  }

  const labels = computed(() =>
    (recap.value?.months ?? []).map((m) =>
      new Date(m.month).toLocaleDateString(undefined, { month: 'short', year: '2-digit' }),
    ),
  )

  function valueFor(month: SportRecap['months'][number]): number {
    if (metric.value === 'distance') return Math.round((month.distance / 1000) * 10) / 10
    if (metric.value === 'moving_time') return Math.round((month.moving_time / 3600) * 10) / 10
    return month.activity_count
  }

  const volumeChart = computed(() => ({
    labels: labels.value,
    datasets: [
      {
        label: RECAP_METRICS.find((m) => m.value === metric.value)!.label,
        data: (recap.value?.months ?? []).map(valueFor),
        backgroundColor: colorForIndex(0),
        borderColor: colorForIndex(0),
        borderRadius: 3,
      },
    ],
  }))

  /**
   * Pace (or speed) against heart rate on one chart.
   *
   * Two axes on purpose: pace falling while heart rate holds or drops is the clearest
   * single picture of getting fitter, and it only reads that way when they're overlaid.
   * The pace axis is reversed so "better" is always up.
   */
  const hasPace = computed(() =>
    (recap.value?.months ?? []).some((m) => m.avg_pace_seconds_per_km !== null),
  )
  const hasSpeed = computed(() => (recap.value?.months ?? []).some((m) => m.avg_speed_kmh !== null))
  const hasHeartrate = computed(() =>
    (recap.value?.months ?? []).some((m) => m.avg_heartrate !== null),
  )
  const showsPerformance = computed(() => hasPace.value || hasSpeed.value || hasHeartrate.value)

  const performanceChart = computed(() => {
    const months = recap.value?.months ?? []
    const datasets = []
    if (hasPace.value) {
      datasets.push({
        type: 'line' as const,
        label: 'Pace (min/km)',
        data: months.map((m) =>
          m.avg_pace_seconds_per_km ? Math.round((m.avg_pace_seconds_per_km / 60) * 100) / 100 : null,
        ),
        borderColor: colorForIndex(0),
        backgroundColor: colorForIndex(0),
        yAxisID: 'rate',
        tension: 0.3,
        spanGaps: true,
      })
    } else if (hasSpeed.value) {
      datasets.push({
        type: 'line' as const,
        label: 'Speed (km/h)',
        data: months.map((m) => m.avg_speed_kmh),
        borderColor: colorForIndex(0),
        backgroundColor: colorForIndex(0),
        yAxisID: 'rate',
        tension: 0.3,
        spanGaps: true,
      })
    }
    if (hasHeartrate.value) {
      datasets.push({
        type: 'line' as const,
        label: 'Avg HR (bpm)',
        data: months.map((m) => m.avg_heartrate),
        borderColor: colorForIndex(2),
        backgroundColor: colorForIndex(2),
        yAxisID: 'hr',
        borderDash: [4, 4],
        tension: 0.3,
        spanGaps: true,
      })
    }
    return { labels: labels.value, datasets }
  })

  const volumeOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, border: { color: chartGrid.value }, ticks: { color: chartInk.value } },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: RECAP_METRICS.find((m) => m.value === metric.value)!.axis,
          color: chartInk.value,
        },
        grid: { color: chartGrid.value },
        border: { display: false },
        ticks: { color: chartInk.value, precision: metric.value === 'activity_count' ? 0 : undefined },
      },
    },
  }))

  const performanceOptions = computed(() => ({
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
      rate: {
        position: 'left' as const,
        // Reversed for pace so improvement always points upwards.
        reverse: hasPace.value,
        title: { display: true, text: hasPace.value ? 'Pace (min/km)' : 'Speed (km/h)', color: chartInk.value },
        grid: { color: chartGrid.value },
        border: { display: false },
        ticks: { color: chartInk.value },
      },
      hr: {
        position: 'right' as const,
        display: hasHeartrate.value,
        title: { display: true, text: 'Avg HR', color: chartInk.value },
        grid: { display: false },
        border: { display: false },
        ticks: { color: chartInk.value },
      },
    },
  }))

  watch([sportType, months], refresh, { immediate: true })

  return {
    recap, metric, isLoading, error, refresh,
    volumeChart, volumeOptions,
    performanceChart, performanceOptions, showsPerformance,
  }
}
