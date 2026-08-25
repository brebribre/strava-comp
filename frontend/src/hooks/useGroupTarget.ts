import { computed, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { MemberProgress, TargetProgress } from '@/types/api'

/** A group's target progress, split into "me" and "everyone else". */
export function useGroupTarget(groupId: () => number, myAthleteId: () => number | undefined) {
  const api = useGroupApi()

  const progress = ref<TargetProgress | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const hasTarget = ref(true)

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      progress.value = await api.targetProgress(id)
      hasTarget.value = true
    } catch (err) {
      // 404 is the normal "no target set yet" answer, not a failure to report.
      if (err instanceof ApiError && err.status === 404) {
        hasTarget.value = false
        progress.value = null
      } else {
        error.value = err instanceof ApiError ? err.message : 'Could not load the target'
      }
    } finally {
      isLoading.value = false
    }
  }

  const me = computed<MemberProgress | null>(
    () => progress.value?.members.find((m) => m.athlete_id === myAthleteId()) ?? null,
  )
  const others = computed<MemberProgress[]>(
    () => progress.value?.members.filter((m) => m.athlete_id !== myAthleteId()) ?? [],
  )

  /** "3 of 4 this week" reads better than a bare percentage. */
  const periodLabel = computed(() => {
    const period = progress.value?.target.period
    return period === 'week' ? 'this week' : period === 'month' ? 'this month' : 'this year'
  })

  const headline = computed(() => {
    if (!progress.value || !me.value) return ''
    if (progress.value.is_expired) return 'This target has ended'
    if (progress.value.is_pending) return 'This target has not started yet'
    if (me.value.is_complete) return `Target hit ${periodLabel.value}`
    const remaining = me.value.remaining
    return `${remaining} more to go ${periodLabel.value}`
  })

  watch([groupId, myAthleteId], refresh, { immediate: true })

  return { progress, me, others, hasTarget, headline, periodLabel, isLoading, error, refresh }
}
