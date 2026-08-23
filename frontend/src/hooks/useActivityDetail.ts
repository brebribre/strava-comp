import { computed, ref, watch } from 'vue'

import { useActivityApi } from '@/api/useActivityApi'
import { ApiError } from '@/api/request'
import { usePolyline } from '@/hooks/usePolyline'
import type { ActivityDetail } from '@/types/api'

export function useActivityDetail(activityId: () => number) {
  const api = useActivityApi()
  const { toSvgPath } = usePolyline()

  const activity = ref<ActivityDetail | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const id = activityId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      activity.value = await api.detail(id)
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load the activity'
      activity.value = null
    } finally {
      isLoading.value = false
    }
  }

  /** SVG path for the GPS trace, or null for indoor activities. */
  const routePath = computed(() => toSvgPath(activity.value?.polyline ?? null))
  const hasRoute = computed(() => routePath.value !== null)

  watch(activityId, refresh, { immediate: true })

  return { activity, routePath, hasRoute, isLoading, error, refresh }
}
