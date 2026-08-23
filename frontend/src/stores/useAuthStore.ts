import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { Athlete } from '@/types/api'

/**
 * Shared session state. Holds state only — the HTTP lives in useAuth/useAuthApi.
 *
 * `resolved` distinguishes "we haven't asked the backend yet" from "we asked and the
 * answer was nobody", which the router guard needs to avoid redirecting on first paint.
 */
export const useAuthStore = defineStore('auth', () => {
  const athlete = ref<Athlete | null>(null)
  const resolved = ref(false)

  function set(next: Athlete | null) {
    athlete.value = next
    resolved.value = true
  }

  function clear() {
    athlete.value = null
    resolved.value = true
  }

  return { athlete, resolved, set, clear }
})
