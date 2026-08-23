import { computed, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import { useAuth } from '@/hooks/useAuth'
import type { GroupMember } from '@/types/api'

export interface MemberRow extends GroupMember {
  isYou: boolean
}

/** The group's members, oldest first, with the logged-in athlete marked. */
export function useGroupMembers(groupId: () => number) {
  const api = useGroupApi()
  const { athlete } = useAuth()

  const members = ref<GroupMember[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      members.value = await api.members(id)
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load members'
      members.value = []
    } finally {
      isLoading.value = false
    }
  }

  const rows = computed<MemberRow[]>(() =>
    members.value.map((member) => ({
      ...member,
      isYou: member.athlete_id === athlete.value?.athlete_id,
    })),
  )

  watch(groupId, refresh, { immediate: true })

  return { rows, isLoading, error, refresh }
}
