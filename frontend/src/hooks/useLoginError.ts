import { computed } from 'vue'

/** Turns the backend's ?error= codes into something a person can read. */
const MESSAGES: Record<string, string> = {
  access_denied: 'You cancelled the Strava authorization.',
  invalid_state: 'That login attempt expired. Please try again.',
  insufficient_scope: 'We need permission to read your activities, including private ones.',
  strava_exchange_failed: 'Strava could not be reached. Please try again.',
  missing_code: 'Strava did not send an authorization code. Please try again.',
  not_found: 'You are logged in, but that invite link is no longer valid.',
}

export function useLoginError(code: () => string | undefined) {
  const message = computed(() => {
    const value = code()
    if (!value) return null
    return MESSAGES[value] ?? 'Login failed. Please try again.'
  })

  return { message }
}
