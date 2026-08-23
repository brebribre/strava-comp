import { navigateTo, request } from '@/api/request'
import type { Athlete } from '@/types/api'

/** Transport only — no state, no redirects beyond the OAuth handoff. */
export function useAuthApi() {
  return {
    me: () => request<Athlete>('GET', '/me'),
    logout: () => request<{ status: string }>('POST', '/auth/logout'),
    /**
     * Full-page redirect to Strava's consent screen; cannot be a fetch.
     *
     * An invite code is passed to the backend, which signs it into the OAuth `state` and
     * joins the group once the athlete exists — so an invite link works for someone who
     * has never logged in.
     */
    startStravaLogin: (inviteCode?: string) =>
      navigateTo(`/auth/strava/login${inviteCode ? `?invite=${encodeURIComponent(inviteCode)}` : ''}`),
  }
}
