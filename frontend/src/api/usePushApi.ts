import { request } from '@/api/request'
import type { PushConfig, PushSubscriptionRead, PushTestResult } from '@/types/api'

/** The browser's subscription, in the shape the backend stores it. */
export interface PushSubscriptionBody {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

export function usePushApi() {
  return {
    config: () => request<PushConfig>('GET', '/push/config'),
    list: () => request<PushSubscriptionRead[]>('GET', '/push/subscriptions'),
    subscribe: (body: PushSubscriptionBody) =>
      request<PushSubscriptionRead>('POST', '/push/subscriptions', body),
    unsubscribe: (body: PushSubscriptionBody) =>
      request<void>('DELETE', '/push/subscriptions', body),
    test: () => request<PushTestResult>('POST', '/push/test'),
  }
}
