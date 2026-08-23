import { computed } from 'vue'

import { useAuthApi } from '@/api/useAuthApi'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/useAuthStore'

/**
 * The session, as containers and the router guard see it.
 *
 * Containers never touch useAuthStore directly — they come through here.
 */
export function useAuth() {
  const store = useAuthStore()
  const api = useAuthApi()

  const athlete = computed(() => store.athlete)
  const isLoggedIn = computed(() => store.athlete !== null)

  /**
   * Ask the backend who we are, once. The session is an HttpOnly cookie, so this is the
   * only way to know — 401 is the normal "logged out" answer, not an error to surface.
   */
  async function resolve(force = false) {
    if (store.resolved && !force) return store.athlete
    try {
      store.set(await api.me())
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) store.clear()
      else store.clear()
    }
    return store.athlete
  }

  async function logout() {
    try {
      await api.logout()
    } finally {
      store.clear()
    }
  }

  return { athlete, isLoggedIn, resolve, logout, login: api.startStravaLogin }
}
