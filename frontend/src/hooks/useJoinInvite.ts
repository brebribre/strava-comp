import { ref } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import { useAuth } from '@/hooks/useAuth'

/**
 * Acting on an invite link.
 *
 * Logged in: join immediately. Logged out: hand the code to the backend through the OAuth
 * flow, which joins once the account exists — so the code survives the trip to Strava
 * without relying on browser storage.
 */
export function useJoinInvite() {
  const api = useGroupApi()
  const { resolve, login } = useAuth()

  const isWorking = ref(true)
  const error = ref<string | null>(null)

  async function accept(inviteCode: string): Promise<number | null> {
    isWorking.value = true
    error.value = null

    const athlete = await resolve()
    if (!athlete) {
      login(inviteCode)
      // The page is navigating away; keep the spinner up until it does.
      return null
    }

    try {
      const group = await api.join(inviteCode)
      return group.id
    } catch (err) {
      error.value =
        err instanceof ApiError && err.status === 404
          ? 'That invite link is not valid any more.'
          : 'Could not join the group.'
      return null
    } finally {
      isWorking.value = false
    }
  }

  return { accept, isWorking, error }
}
