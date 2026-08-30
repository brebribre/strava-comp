<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import AppAvatar from '@/reusables/AppAvatar.vue'
import IconSettings from '~icons/material-symbols/settings-rounded'

/**
 * The phone's top bar. There is no navigation in it — the bottom tabs do that — so it
 * carries who you are on the left and the one account action on the right.
 */
const router = useRouter()
const { athlete, logout } = useAuth()
const { initials, firstName } = useFormat()

const isMenuOpen = ref(false)

function openNotifications() {
  isMenuOpen.value = false
  router.push({ name: 'notifications' })
}

async function handleLogout() {
  isMenuOpen.value = false
  await logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="relative flex items-center justify-between gap-3 px-4 py-3">
    <div class="flex min-w-0 items-center gap-2.5">
      <AppAvatar
        v-if="athlete"
        :initials="initials(athlete.name)"
        :color-seed="athlete.athlete_id"
      />
      <p class="truncate text-base font-semibold text-ink">
        {{ athlete ? firstName(athlete.name) : '…' }}
      </p>
    </div>

    <button
      type="button"
      aria-label="Account settings"
      :aria-expanded="isMenuOpen"
      class="-mr-1 rounded-lg p-2 text-ink-muted transition-colors duration-(--duration-quick) hover:bg-raised"
      @click="isMenuOpen = !isMenuOpen"
    >
      <IconSettings class="size-6" aria-hidden="true" />
    </button>

    <!-- Tap-anywhere-to-close, the way a native sheet behaves. -->
    <div v-if="isMenuOpen" class="fixed inset-0 z-20" @click="isMenuOpen = false" />

    <div
      v-if="isMenuOpen"
      class="animate-rise absolute right-3 top-full z-30 w-40 rounded-lg bg-raised p-1 shadow-lg shadow-black/40"
    >
      <button
        type="button"
        class="w-full rounded-md px-3 py-2 text-left text-sm text-ink transition-colors duration-(--duration-quick) hover:bg-surface"
        @click="openNotifications"
      >
        Notifications
      </button>
      <button
        type="button"
        class="w-full rounded-md px-3 py-2 text-left text-sm text-ink transition-colors duration-(--duration-quick) hover:bg-surface"
        @click="handleLogout"
      >
        Log out
      </button>
    </div>
  </header>
</template>
