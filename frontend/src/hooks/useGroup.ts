import { ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { Group } from '@/types/api'

/**
 * One group's details.
 *
 * There's no GET /groups/{id} on the backend, so this filters the athlete's group list —
 * which is also the membership check, since the list only contains groups they belong to.
 */
export function useGroup(groupId: () => number) {
  const api = useGroupApi()

  const group = ref<Group | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      group.value = (await api.list()).find((candidate) => candidate.id === id) ?? null
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load the group'
      group.value = null
    } finally {
      isLoading.value = false
    }
  }

  watch(groupId, refresh, { immediate: true })

  return { group, isLoading, error, refresh }
}
