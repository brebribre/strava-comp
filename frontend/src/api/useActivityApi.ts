import { request } from '@/api/request'
import type { ActivityDetail, SyncResult } from '@/types/api'

export function useActivityApi() {
  return {
    sync: (days?: number) =>
      request<SyncResult>('POST', `/activities/sync${days ? `?days=${days}` : ''}`),
    detail: (activityId: number) => request<ActivityDetail>('GET', `/activities/${activityId}`),
  }
}
