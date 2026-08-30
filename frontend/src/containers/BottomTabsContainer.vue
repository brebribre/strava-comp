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
  <!-- A floating bar, but one that still reaches the bottom of the screen. The home
       indicator's inset is paid *inside* the card rather than under it: spending it as
       margin would park the bar 34px up and leave a dead strip of background beneath,
       which is not what a phone's tab bar looks like. Everywhere without an indicator the
       inset is 0 and the card keeps its plain padding. -->
  <nav class="px-3 pb-2 pt-1" aria-label="Primary">
    <div
      class="flex gap-1 rounded-2xl bg-surface p-1.5 pb-[max(0.375rem,calc(env(safe-area-inset-bottom)-0.5rem))] shadow-lg shadow-black/40"
    >
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
