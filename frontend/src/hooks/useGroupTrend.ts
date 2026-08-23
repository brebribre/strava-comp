import { computed, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { GroupTrend } from '@/types/api'

/** Palette for chart series. Canvas can't read Tailwind classes, so colours live here. */
const SERIES_COLOURS = ['#fc4c02', '#2563eb', '#16a34a', '#9333ea', '#dc2626', '#0891b2']

export type TrendMetric = 'moving_time' | 'activity_count'

export const TREND_METRICS: { value: TrendMetric; label: string; axis: string }[] = [
  { value: 'moving_time', label: 'Moving time', axis: 'Minutes moving' },
  { value: 'activity_count', label: 'Activities', axis: 'Activities' },
]

export function useGroupTrend(groupId: () => number, days: () => number) {
  const api = useGroupApi()

  const metric = ref<TrendMetric>('moving_time')
  const trend = ref<GroupTrend | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      trend.value = await api.trend(id, days())
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load the trend'
      trend.value = null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Chart.js data, built here rather than in the container.
   *
   * Members report only the weeks they were active, so the union of all week_starts
   * becomes the shared x-axis and each member is padded with zeroes — otherwise series
   * would be misaligned against each other.
   */
  const chartData = computed(() => {
    const members = trend.value?.members ?? []
    const weeks = [...new Set(members.flatMap((m) => m.weeks.map((w) => w.week_start)))].sort()

    return {
      labels: weeks.map((w) =>
        new Date(w).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      ),
      datasets: members.map((member, index) => ({
        label: member.name,
        data: weeks.map((week) => {
          const point = member.weeks.find((w) => w.week_start === week)
          if (!point) return 0
          return metric.value === 'activity_count'
            ? point.activity_count
            : Math.round((point.total_moving_time / 60) * 10) / 10
        }),
        backgroundColor: SERIES_COLOURS[index % SERIES_COLOURS.length],
        borderColor: SERIES_COLOURS[index % SERIES_COLOURS.length],
        borderRadius: 4,
      })),
    }
  })

  const hasData = computed(() =>
    (trend.value?.members ?? []).some((m) => m.weeks.length > 0),
  )

  const chartOptions = computed(() => {
    const unit = metric.value === 'activity_count' ? '' : ' min'
    const axis = TREND_METRICS.find((m) => m.value === metric.value)!.axis
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' as const },
        tooltip: {
          callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${ctx.parsed.y}${unit}` },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: axis },
          // Activity counts are whole numbers; fractional ticks would be nonsense.
          ticks: metric.value === 'activity_count' ? { precision: 0 } : {},
        },
      },
    }
  })

  // Only the window and group need a refetch — switching metric re-derives from the same data.
  watch([groupId, days], refresh, { immediate: true })

  return { trend, metric, chartData, chartOptions, hasData, isLoading, error, refresh }
}
