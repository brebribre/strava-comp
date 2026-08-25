<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import IconGroups from '~icons/material-symbols/groups-rounded'
import IconRecap from '~icons/material-symbols/insights'

/**
 * The phone's primary navigation, in the place a native app puts it. The drawer still holds
 * the full group list and logging out; this is the two-thumb switch between the personal
 * recap and everything group-shaped.
 */
const route = useRoute()
const router = useRouter()

const tabs = [
  { key: 'recap', label: 'Recap', icon: IconRecap, to: { name: 'recap' } },
  { key: 'groups', label: 'Groups', icon: IconGroups, to: { name: 'groups' } },
] as const

/** A tab owns everything under it: /recap/Run keeps Recap lit, /groups/5/feed keeps Groups. */
function isActive(key: string): boolean {
  const name = String(route.name ?? '')
  return key === 'recap' ? name.startsWith('recap') : name.startsWith('group')
}
</script>

<template>
  <!-- A floating bar rather than one welded to the bottom edge: it sits inset from the
       screen with the home indicator's safe area under it, and takes its edge from the
       surface tint like every other card. -->
  <nav class="px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-1" aria-label="Primary">
    <div class="flex gap-1 rounded-2xl bg-surface p-1.5 shadow-lg shadow-black/40">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :aria-current="isActive(tab.key) ? 'page' : undefined"
        :class="[
          'flex flex-1 flex-col items-center gap-0.5 rounded-xl px-2 py-2',
          'transition-colors duration-(--duration-quick)',
          isActive(tab.key) ? 'bg-accent-soft text-accent' : 'text-ink-subtle',
        ]"
        @click="router.push(tab.to)"
      >
        <component :is="tab.icon" class="size-6" aria-hidden="true" />
        <span class="text-[11px] font-medium tracking-wide">{{ tab.label }}</span>
      </button>
    </div>
  </nav>
</template>
