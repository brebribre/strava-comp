import { request } from '@/api/request'
import type { RecapOverview, SportRecap, ZoneRecap } from '@/types/api'

/** Personal recap — no group involved. */
export function useRecapApi() {
  return {
    overview: (days: number) => request<RecapOverview>('GET', `/recap?days=${days}`),
    sport: (sportType: string, months: number) =>
      request<SportRecap>('GET', `/recap/${encodeURIComponent(sportType)}?months=${months}`),
    zones: (sportType: string, months: number) =>
      request<ZoneRecap>('GET', `/recap/${encodeURIComponent(sportType)}/zones?months=${months}`),
  }
}
