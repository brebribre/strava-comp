import { ref } from 'vue'

import { useActivityApi } from '@/api/useActivityApi'
import { ApiError } from '@/api/request'

/** Manual "pull my latest activities from Strava" action. */
export function useActivitySync() {
  const api = useActivityApi()

  const isSyncing = ref(false)
  const lastResult = ref<string | null>(null)
  const error = ref<string | null>(null)

  async function sync(days?: number) {
    isSyncing.value = true
    error.value = null
    lastResult.value = null
    try {
      const result = await api.sync(days)
      lastResult.value = `Synced ${result.activities_saved} activities`
      return true
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Sync failed'
      return false
    } finally {
      isSyncing.value = false
    }
  }

  return { sync, isSyncing, lastResult, error }
}
