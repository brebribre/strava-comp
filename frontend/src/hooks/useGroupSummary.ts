import { ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { GroupSummary, MemberSummary } from '@/types/api'

export const WINDOW_OPTIONS = [7, 30, 90] as const

/** One group's summary for a selectable window. */
export function useGroupSummary(groupId: () => number) {
  const api = useGroupApi()

  const summary = ref<GroupSummary | null>(null)
  const members = ref<MemberSummary[]>([])
  const days = ref<number>(30)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      const result = await api.summary(id, days.value)
      summary.value = result
      // The backend already orders by moving time; keep that order.
      members.value = result.members
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load the summary'
      summary.value = null
      members.value = []
    } finally {
      isLoading.value = false
    }
  }

  watch([groupId, days], refresh, { immediate: true })

  return { summary, members, days, isLoading, error, refresh }
}
