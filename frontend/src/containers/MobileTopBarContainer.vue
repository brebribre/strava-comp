<script setup lang="ts">
import { useSidebar } from '@/hooks/useSidebar'

const { toggle } = useSidebar()
</script>

<template>
  <header
    class="flex items-center gap-3 border-b border-line bg-surface px-4 py-3"
  >
    <button
      type="button"
      aria-label="Open navigation"
      class="-ml-2 rounded-lg p-2 text-ink-muted hover:bg-raised"
      @click="toggle"
    >
      <svg class="size-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
    <p class="text-sm font-semibold text-ink">Strava Group Tracker</p>
  </header>
</template>
