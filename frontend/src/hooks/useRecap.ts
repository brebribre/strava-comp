import { computed, ref, watch } from 'vue'

import { useRecapApi } from '@/api/useRecapApi'
import { ApiError } from '@/api/request'
import type { RecapOverview } from '@/types/api'

export const RECAP_WINDOWS = [
  { days: 90, label: '3 months' },
  { days: 180, label: '6 months' },
  { days: 365, label: '1 year' },
  { days: 1095, label: 'All time' },
] as const

export function useRecap() {
  const api = useRecapApi()

  const overview = ref<RecapOverview | null>(null)
  const days = ref<number>(365)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      overview.value = await api.overview(days.value)
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load your recap'
      overview.value = null
    } finally {
      isLoading.value = false
    }
  }

  const sports = computed(() => overview.value?.sports ?? [])
  const hasData = computed(() => (overview.value?.total.activity_count ?? 0) > 0)

  /**
   * Growth is only shown when the comparison window is actually covered by history.
   * Otherwise the percentages measure when tracking started, not any change in training.
   */
  const showsGrowth = computed(() => overview.value?.baseline_complete ?? false)

  function growth(current: number, previous: number): number | null {
    if (!showsGrowth.value || !previous) return null
    return ((current - previous) / previous) * 100
  }

  const totalGrowth = computed(() => ({
    activity_count: growth(
      overview.value?.total.activity_count ?? 0,
      overview.value?.previous_total.activity_count ?? 0,
    ),
    distance: growth(overview.value?.total.distance ?? 0, overview.value?.previous_total.distance ?? 0),
    moving_time: growth(
      overview.value?.total.moving_time ?? 0,
      overview.value?.previous_total.moving_time ?? 0,
    ),
  }))

  watch(days, refresh, { immediate: true })

  return { overview, sports, days, hasData, showsGrowth, totalGrowth, isLoading, error, refresh }
}
