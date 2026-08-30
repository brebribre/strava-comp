/*
 * Service worker: the only thing on the page that can receive a push.
 *
 * Deliberately no caching. An offline cache would mean stale activity data and a second
 * source of truth to invalidate; the one job here is notifications.
 */

self.addEventListener('install', () => {
  // Take over immediately instead of waiting for every tab to close — an update to this
  // file should not need the web app to be quit and reopened.
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  // A push with no readable body still has to show something: iOS revokes permission from
  // a site that receives a push and displays no notification.
  let payload = { title: 'Bruderbande', body: 'Someone finished a workout.', url: '/' }
  try {
    if (event.data) payload = { ...payload, ...event.data.json() }
  } catch {
    /* keep the fallback */
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      // Same tag per activity, so a repeated delivery replaces rather than stacks.
      tag: payload.activity_id ? `activity-${payload.activity_id}` : 'bruderbande',
      data: { url: payload.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.url || '/', self.location.origin).href

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Reuse the installed web app's window if it is already open; opening a second one
      // is what makes a PWA feel like a browser again.
      for (const client of clients) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          client.navigate(target)
          return client.focus()
        }
      }
      return self.clients.openWindow(target)
    }),
  )
})
