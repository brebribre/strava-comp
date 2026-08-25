<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useGroups } from '@/hooks/useGroups'
import { useSidebar } from '@/hooks/useSidebar'
import AppButton from '@/reusables/AppButton.vue'
import AppLogo from '@/reusables/AppLogo.vue'
import SportLoader from '@/reusables/SportLoader.vue'

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
    class="fixed inset-0 z-30 bg-ink/25 lg:hidden"
    aria-hidden="true"
    @click="close"
  />

  <aside
    :class="[
      'flex w-64 shrink-0 flex-col border-r border-line bg-surface',
      // Off-canvas on phones, always in flow from lg up.
      'fixed inset-y-0 left-0 z-40 lg:static lg:z-auto lg:translate-x-0',
      'transition-transform duration-(--duration-soft) ease-(--ease-out-soft)',
      isOpen ? 'translate-x-0' : '-translate-x-full',
    ]"
  >
    <div class="flex items-start justify-between border-b border-line p-4">
      <div class="min-w-0">
        <AppLogo size="sm" />
        <p class="mt-2 truncate text-xs text-ink-muted">{{ athlete?.name ?? '…' }}</p>
      </div>
      <button
        type="button"
        aria-label="Close navigation"
        class="-mr-2 -mt-1 rounded-lg p-2 text-ink-muted hover:bg-raised lg:hidden"
        @click="close"
      >
        <svg class="size-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <nav class="flex-1 overflow-y-auto p-2">
      <p class="px-2 py-1 text-[11px] font-medium uppercase tracking-wider text-ink-subtle">You</p>
      <button
        :class="[
          'mb-3 block w-full rounded-md px-3 py-2 text-left text-sm transition-colors duration-(--duration-quick)',
          route.name === 'recap' || route.name === 'recap-sport'
            ? 'bg-accent-soft font-medium text-accent'
            : 'text-ink-muted hover:bg-raised hover:text-ink',
        ]"
        @click="router.push({ name: 'recap' })"
      >
        Recap
      </button>

      <button
        :class="[
          'mb-3 block w-full rounded-md px-3 py-2 text-left text-sm',
          'transition-colors duration-(--duration-quick)',
          route.name === 'appearance'
            ? 'bg-accent-soft font-medium text-accent'
            : 'text-ink-muted hover:bg-raised hover:text-ink',
        ]"
        @click="router.push({ name: 'appearance' })"
      >
        Appearance
      </button>

      <p class="px-2 py-1 text-[11px] font-medium uppercase tracking-wider text-ink-subtle">Groups</p>
      <SportLoader v-if="isLoading" :size="26" class="py-4" />
      <p v-else-if="!groups.length" class="px-2 py-2 text-sm text-ink-subtle">No groups yet</p>
      <button
        v-for="group in groups"
        :key="group.id"
        :class="[
          'mb-1 block w-full truncate rounded-md px-3 py-2 text-left text-sm',
          'transition-colors duration-(--duration-quick)',
          Number(route.params.id) === group.id
            ? 'bg-accent-soft font-medium text-accent'
            : 'text-ink-muted hover:bg-raised hover:text-ink',
        ]"
        @click="openGroup(group.id)"
      >
        {{ group.name }}
        <span class="text-xs text-ink-subtle">· {{ group.member_count }}</span>
      </button>
    </nav>

    <div class="border-t border-line p-2">
      <AppButton variant="ghost" class="w-full" @click="router.push({ name: 'groups' })">
        Manage groups
      </AppButton>
      <AppButton variant="ghost" class="w-full" @click="handleLogout">Log out</AppButton>
    </div>
  </aside>
</template>
