import { computed, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import { useSportColors } from '@/hooks/useSportColors'
import type { GroupTrend } from '@/types/api'

/** Colours for per-member series (moving-time mode). Sports have their own palette. */
const MEMBER_COLOURS = ['#fc4c02', '#2563eb', '#16a34a', '#9333ea', '#dc2626', '#0891b2']

export type TrendMetric = 'moving_time' | 'activity_count'

export const TREND_METRICS: { value: TrendMetric; label: string; axis: string }[] = [
  { value: 'moving_time', label: 'Moving time', axis: 'Minutes moving' },
  { value: 'activity_count', label: 'Activities', axis: 'Activities' },
]

export function useGroupTrend(groupId: () => number, days: () => number) {
  const api = useGroupApi()
  const { colorFor } = useSportColors()

  const metric = ref<TrendMetric>('moving_time')
  const trend = ref<GroupTrend | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Empty set means "no filter" — simpler than seeding with every value and keeping the
  // two in sync as data arrives.
  const sportFilter = ref<Set<string>>(new Set())
  const athleteFilter = ref<Set<number>>(new Set())

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

  const availableSports = computed(() => {
    const sports = new Set<string>()
    for (const member of trend.value?.members ?? []) {
      for (const week of member.weeks) {
        for (const bucket of week.by_sport) sports.add(bucket.sport_type)
      }
    }
    return [...sports].sort()
  })

  const availableAthletes = computed(() =>
    (trend.value?.members ?? []).map((m) => ({ id: m.athlete_id, name: m.name })),
  )

  function toggleSport(sport: string) {
    const next = new Set(sportFilter.value)
    next.has(sport) ? next.delete(sport) : next.add(sport)
    sportFilter.value = next
  }

  function toggleAthlete(athleteId: number) {
    const next = new Set(athleteFilter.value)
    next.has(athleteId) ? next.delete(athleteId) : next.add(athleteId)
    athleteFilter.value = next
  }

  function clearFilters() {
    sportFilter.value = new Set()
    athleteFilter.value = new Set()
  }

  const hasFilters = computed(() => sportFilter.value.size > 0 || athleteFilter.value.size > 0)

  function sportIncluded(sport: string) {
    return sportFilter.value.size === 0 || sportFilter.value.has(sport)
  }
  function athleteIncluded(athleteId: number) {
    return athleteFilter.value.size === 0 || athleteFilter.value.has(athleteId)
  }

  /** Members left after the athlete filter, with each week's sports filtered too. */
  const visibleMembers = computed(() =>
    (trend.value?.members ?? [])
      .filter((member) => athleteIncluded(member.athlete_id))
      .map((member) => ({
        ...member,
        weeks: member.weeks.map((week) => ({
          ...week,
          by_sport: week.by_sport.filter((bucket) => sportIncluded(bucket.sport_type)),
        })),
      })),
  )

  /** Shared x-axis: members only report weeks they were active in. */
  const weekKeys = computed(() =>
    [
      ...new Set(visibleMembers.value.flatMap((m) => m.weeks.map((w) => w.week_start))),
    ].sort(),
  )

  const labels = computed(() =>
    weekKeys.value.map((week) =>
      new Date(week).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    ),
  )

  /**
   * Two different shapes:
   * - moving time  → one series per member, for comparing people
   * - activities   → one series per *sport*, stacked, for seeing what the training was made of
   */
  const chartData = computed(() => {
    if (metric.value === 'activity_count') {
      const sports = availableSports.value.filter(sportIncluded)
      return {
        labels: labels.value,
        datasets: sports.map((sport) => ({
          label: sport,
          data: weekKeys.value.map((week) =>
            visibleMembers.value.reduce((total, member) => {
              const point = member.weeks.find((w) => w.week_start === week)
              const bucket = point?.by_sport.find((b) => b.sport_type === sport)
              return total + (bucket?.activity_count ?? 0)
            }, 0),
          ),
          backgroundColor: colorFor(sport),
          borderColor: colorFor(sport),
          borderRadius: 3,
          stack: 'activities',
        })),
      }
    }

    return {
      labels: labels.value,
      datasets: visibleMembers.value.map((member, index) => ({
        label: member.name,
        data: weekKeys.value.map((week) => {
          const point = member.weeks.find((w) => w.week_start === week)
          if (!point) return 0
          const seconds = point.by_sport.reduce((total, b) => total + b.total_moving_time, 0)
          return Math.round((seconds / 60) * 10) / 10
        }),
        backgroundColor: MEMBER_COLOURS[index % MEMBER_COLOURS.length],
        borderColor: MEMBER_COLOURS[index % MEMBER_COLOURS.length],
        borderRadius: 4,
      })),
    }
  })

  const chartOptions = computed(() => {
    const stacked = metric.value === 'activity_count'
    const unit = stacked ? '' : ' min'
    const axis = TREND_METRICS.find((m) => m.value === metric.value)!.axis
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' as const },
        tooltip: {
          // Stacked bars are only readable if the tooltip shows the whole week.
          mode: stacked ? ('index' as const) : ('nearest' as const),
          intersect: !stacked,
          callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${ctx.parsed.y}${unit}` },
        },
      },
      scales: {
        x: { stacked },
        y: {
          stacked,
          beginAtZero: true,
          title: { display: true, text: axis },
          ticks: stacked ? { precision: 0 } : {},
        },
      },
    }
  })

  const hasData = computed(() =>
    chartData.value.datasets.some((dataset) => dataset.data.some((value) => value > 0)),
  )

  watch([groupId, days], refresh, { immediate: true })

  return {
    trend,
    metric,
    chartData,
    chartOptions,
    hasData,
    isLoading,
    error,
    refresh,
    availableSports,
    availableAthletes,
    sportFilter,
    athleteFilter,
    toggleSport,
    toggleAthlete,
    clearFilters,
    hasFilters,
  }
}
