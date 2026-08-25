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
          path: 'appearance',
          name: 'appearance',
          component: () => import('@/containers/AppearanceContainer.vue'),
        },
        {
          path: 'recap',
          name: 'recap',
          component: () => import('@/containers/RecapOverviewContainer.vue'),
        },
        {
          path: 'recap/:sport',
          name: 'recap-sport',
          component: () => import('@/containers/SportRecapContainer.vue'),
        },
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
            // Summary first: it leads with the target and the week-by-week progress,
            // which is what people open the group to see.
            { path: '', name: 'group', redirect: { name: 'group-summary' } },
            {
              path: 'summary',
              name: 'group-summary',
              component: () => import('@/containers/GroupSummaryContainer.vue'),
            },
            {
              path: 'feed',
              name: 'group-feed',
              component: () => import('@/containers/GroupFeedContainer.vue'),
            },
            {
              path: 'settings',
              component: () => import('@/views/GroupSettingsView.vue'),
              children: [
                { path: '', name: 'group-settings', redirect: { name: 'group-settings-members' } },
                {
                  path: 'members',
                  name: 'group-settings-members',
                  component: () => import('@/containers/GroupMembersContainer.vue'),
                },
                {
                  path: 'target',
                  name: 'group-settings-target',
                  component: () => import('@/containers/GroupTargetSettingsContainer.vue'),
                },
                {
                  path: 'notifications',
                  name: 'group-settings-notifications',
                  component: () => import('@/containers/GroupNotificationsContainer.vue'),
                },
              ],
            },
            // Old links kept working rather than 404ing.
            { path: 'target', redirect: { name: 'group-summary' } },
            { path: 'members', redirect: { name: 'group-settings-members' } },
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

  /**
   * Landing back from OAuth.
   *
   * The backend redirects to FRONTEND_ORIGIN itself, so this arrives on `/` — not on
   * `/login`. Keying off `?login=ok` instead of the route name handles both, which the
   * earlier route-name check did not: following an invite link dropped you on the group
   * list instead of the group you had just joined.
   */
  if (athlete && to.query.login === 'ok') {
    const joined = Number(to.query.group)
    return Number.isFinite(joined) && joined > 0
      ? { name: 'group-feed', params: { id: joined } }
      : { name: 'groups' }
  }

  // Already logged in but sitting on the login page — nothing to do here.
  if (to.name === 'login' && athlete) {
    return { name: 'groups' }
  }
  return true
})

export default router
