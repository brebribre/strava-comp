import { computed, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePushApi } from '@/api/usePushApi'

/**
 * Web push, and everything iOS insists on before it will work.
 *
 * On iPhone this only exists inside a web app added to the Home Screen — Safari tabs have
 * no Push API at all — and permission may only be asked for from a real tap. Both of those
 * are surfaced as state rather than hidden, because a button that silently does nothing is
 * worse than one that explains why it is disabled.
 */
export function usePushNotifications() {
  const api = usePushApi()

  const isSupported = ref(
    typeof window !== 'undefined' &&
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window,
  )
  const permission = ref<NotificationPermission>(
    typeof Notification === 'undefined' ? 'default' : Notification.permission,
  )
  const isSubscribed = ref(false)
  const isBusy = ref(false)
  const error = ref<string | null>(null)
  const message = ref<string | null>(null)
  const serverEnabled = ref(false)

  /** iOS gives a web app the Push API only once it has been installed to the Home Screen. */
  const isStandalone = computed(
    () =>
      window.matchMedia('(display-mode: standalone)').matches ||
      // Safari's own flag, which predates the standard media query.
      (window.navigator as unknown as { standalone?: boolean }).standalone === true,
  )

  const isIos = computed(() =>
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    // iPadOS reports itself as a Mac, but with a touch screen.
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1),
  )

  /** The one case worth explaining in words: an iPhone in a Safari tab. */
  const needsInstall = computed(() => isIos.value && !isStandalone.value)

  const isBlocked = computed(() => permission.value === 'denied')

  /** VAPID keys travel as base64url; PushManager wants the raw bytes. */
  function decodeKey(base64Url: string): ArrayBuffer {
    const padded = base64Url.padEnd(base64Url.length + ((4 - (base64Url.length % 4)) % 4), '=')
    const binary = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
    return bytes.buffer
  }

  function toBody(subscription: PushSubscription) {
    const json = subscription.toJSON()
    return {
      endpoint: subscription.endpoint,
      keys: { p256dh: json.keys?.p256dh ?? '', auth: json.keys?.auth ?? '' },
    }
  }

  async function registration(): Promise<ServiceWorkerRegistration> {
    return navigator.serviceWorker.register('/sw.js', { scope: '/' })
  }

  /** Reads the browser's current state; safe to call on mount. */
  async function refresh() {
    if (!isSupported.value) return
    try {
      const config = await api.config()
      serverEnabled.value = config.enabled
      permission.value = Notification.permission
      const existing = await (await registration()).pushManager.getSubscription()
      isSubscribed.value = existing !== null
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not check notifications'
    }
  }

  /** Must be called straight from a click: iOS ignores a permission prompt otherwise. */
  async function enable(): Promise<boolean> {
    error.value = null
    message.value = null
    isBusy.value = true
    try {
      const config = await api.config()
      serverEnabled.value = config.enabled
      if (!config.enabled || !config.public_key) {
        error.value = 'This server has no push keys configured.'
        return false
      }

      permission.value = await Notification.requestPermission()
      if (permission.value !== 'granted') {
        error.value =
          permission.value === 'denied'
            ? 'Notifications are blocked for this app in your device settings.'
            : 'Notifications were not allowed.'
        return false
      }

      const reg = await registration()
      // An existing subscription is reused; the browser returns the same endpoint anyway.
      const subscription =
        (await reg.pushManager.getSubscription()) ??
        (await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: decodeKey(config.public_key),
        }))

      await api.subscribe(toBody(subscription))
      isSubscribed.value = true
      message.value = 'This device will now be notified.'
      return true
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not turn notifications on'
      return false
    } finally {
      isBusy.value = false
    }
  }

  async function disable(): Promise<boolean> {
    error.value = null
    message.value = null
    isBusy.value = true
    try {
      const reg = await registration()
      const subscription = await reg.pushManager.getSubscription()
      if (subscription) {
        // Tell the server first: a subscription it still holds would keep failing, while
        // an orphan in the browser is harmless.
        await api.unsubscribe(toBody(subscription)).catch(() => undefined)
        await subscription.unsubscribe()
      }
      isSubscribed.value = false
      message.value = 'This device will no longer be notified.'
      return true
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not turn notifications off'
      return false
    } finally {
      isBusy.value = false
    }
  }

  async function sendTest() {
    error.value = null
    message.value = null
    isBusy.value = true
    try {
      const result = await api.test()
      message.value = result.delivered
        ? `Sent to ${result.delivered} device${result.delivered === 1 ? '' : 's'}.`
        : result.detail
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not send a test'
    } finally {
      isBusy.value = false
    }
  }

  return {
    isSupported,
    serverEnabled,
    permission,
    isSubscribed,
    isBusy,
    isBlocked,
    isStandalone,
    needsInstall,
    error,
    message,
    refresh,
    enable,
    disable,
    sendTest,
  }
}
