<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useGroups } from '@/hooks/useGroups'
import AppButton from '@/reusables/AppButton.vue'

const route = useRoute()
const router = useRouter()
const { athlete, logout } = useAuth()
const { groups, isLoading, refresh } = useGroups()

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
  <aside
    class="flex h-full flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"
  >
    <div class="border-b border-slate-200 p-4 dark:border-slate-700">
      <p class="text-sm font-semibold text-slate-900 dark:text-slate-100">
        {{ athlete?.name ?? '…' }}
      </p>
      <p class="text-xs text-slate-500 dark:text-slate-400">Strava Group Tracker</p>
    </div>

    <nav class="flex-1 overflow-y-auto p-2">
      <p class="px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-400">Groups</p>
      <p v-if="isLoading" class="px-2 py-2 text-sm text-slate-400">Loading…</p>
      <p v-else-if="!groups.length" class="px-2 py-2 text-sm text-slate-400">No groups yet</p>
      <button
        v-for="group in groups"
        :key="group.id"
        :class="[
          'mb-1 block w-full rounded-lg px-3 py-2 text-left text-sm transition',
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
