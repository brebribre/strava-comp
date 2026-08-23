import { ref } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { Group } from '@/types/api'

/** The athlete's groups, plus creating and joining. */
export function useGroups() {
  const api = useGroupApi()

  const groups = ref<Group[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      groups.value = await api.list()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load groups'
    } finally {
      isLoading.value = false
    }
  }

  async function create(name: string): Promise<Group | null> {
    error.value = null
    try {
      const group = await api.create(name)
      await refresh()
      return group
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not create the group'
      return null
    }
  }

  async function join(inviteCode: string): Promise<Group | null> {
    error.value = null
    try {
      const group = await api.join(inviteCode)
      await refresh()
      return group
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not join the group'
      return null
    }
  }

  return { groups, isLoading, error, refresh, create, join }
}
