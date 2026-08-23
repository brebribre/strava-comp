<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useGroups } from '@/hooks/useGroups'
import { useSidebar } from '@/hooks/useSidebar'
import AppButton from '@/reusables/AppButton.vue'

const route = useRoute()
const router = useRouter()
const { athlete, logout } = useAuth()
const { groups, isLoading, refresh } = useGroups()
const { isOpen, close } = useSidebar()

onMounted(refresh)

function openGroup(id: number) {
  router.push({ name: 'group', params: { id } })
}

async function handleLogout() {
  await logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <!-- Backdrop only exists while the drawer is open on small screens. -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-30 bg-slate-900/50 lg:hidden"
    aria-hidden="true"
    @click="close"
  />

  <aside
    :class="[
      'flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900',
      // Off-canvas on phones, always in flow from lg up.
      'fixed inset-y-0 left-0 z-40 transition-transform lg:static lg:z-auto lg:translate-x-0',
      isOpen ? 'translate-x-0' : '-translate-x-full',
    ]"
  >
    <div class="flex items-start justify-between border-b border-slate-200 p-4 dark:border-slate-700">
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
          {{ athlete?.name ?? '…' }}
        </p>
        <p class="text-xs text-slate-500 dark:text-slate-400">Strava Group Tracker</p>
      </div>
      <button
        type="button"
        aria-label="Close navigation"
        class="-mr-2 -mt-1 rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"
        @click="close"
      >
        <svg class="size-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <nav class="flex-1 overflow-y-auto p-2">
      <p class="px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-400">Groups</p>
      <p v-if="isLoading" class="px-2 py-2 text-sm text-slate-400">Loading…</p>
      <p v-else-if="!groups.length" class="px-2 py-2 text-sm text-slate-400">No groups yet</p>
      <button
        v-for="group in groups"
        :key="group.id"
        :class="[
          'mb-1 block w-full truncate rounded-lg px-3 py-2 text-left text-sm transition',
          Number(route.params.id) === group.id
            ? 'bg-strava/10 font-medium text-strava'
            : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
        ]"
        @click="openGroup(group.id)"
      >
        {{ group.name }}
        <span class="text-xs text-slate-400">· {{ group.member_count }}</span>
      </button>
    </nav>

    <div class="border-t border-slate-200 p-2 dark:border-slate-700">
      <AppButton variant="ghost" class="w-full" @click="router.push({ name: 'groups' })">
        Manage groups
      </AppButton>
      <AppButton variant="ghost" class="w-full" @click="handleLogout">Log out</AppButton>
    </div>
  </aside>
</template>
