import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      // Public: an invite link must work for someone with no account yet.
      path: '/join/:code',
      name: 'join',
      component: () => import('@/views/JoinView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/views/SidebarView.vue'),
      children: [
        { path: '', redirect: { name: 'groups' } },
        {
          path: 'groups',
          name: 'groups',
          component: () => import('@/containers/GroupListContainer.vue'),
        },
        {
          path: 'groups/:id',
          // A view that itself hosts a router-view: the tabs stay mounted while the
          // active tab's container swaps underneath.
          component: () => import('@/views/GroupView.vue'),
          children: [
            { path: '', name: 'group', redirect: { name: 'group-feed' } },
            {
              path: 'feed',
              name: 'group-feed',
              component: () => import('@/containers/GroupFeedContainer.vue'),
            },
            {
              path: 'summary',
              name: 'group-summary',
              component: () => import('@/containers/GroupSummaryContainer.vue'),
            },
            {
              path: 'target',
              name: 'group-target',
              component: () => import('@/containers/GroupTargetContainer.vue'),
            },
            {
              path: 'settings',
              name: 'group-settings',
              component: () => import('@/containers/GroupSettingsContainer.vue'),
            },
            {
              path: 'activities/:activityId',
              name: 'activity',
              component: () => import('@/containers/ActivityDetailContainer.vue'),
            },
          ],
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'groups' } },
  ],
})

/**
 * Auth is enforced here, once — not in each container.
 *
 * The session is an HttpOnly cookie, so the only way to know whether we're logged in is
 * to ask the backend. useAuth().resolve() caches that answer for the session.
 */
router.beforeEach(async (to) => {
  const { resolve } = useAuth()
  const athlete = await resolve()

  if (!to.meta.public && !athlete) {
    return { name: 'login' }
  }
  // Already logged in and heading to the login page — the OAuth redirect lands here
  // with ?login=ok, so send them on to the app.
  if (to.name === 'login' && athlete) {
    // Followed an invite link while logged out: the backend already joined them and
    // named the group, so land them in it rather than on the group list.
    const joined = Number(to.query.group)
    if (Number.isFinite(joined) && joined > 0) {
      return { name: 'group-feed', params: { id: joined } }
    }
    return { name: 'groups' }
  }
  return true
})

export default router
