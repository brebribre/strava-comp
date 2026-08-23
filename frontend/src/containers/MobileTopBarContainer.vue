<script setup lang="ts">
import { useSidebar } from '@/hooks/useSidebar'

const { toggle } = useSidebar()
</script>

<template>
  <header
    class="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900"
  >
    <button
      type="button"
      aria-label="Open navigation"
      class="-ml-2 rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
      @click="toggle"
    >
      <svg class="size-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
    <p class="text-sm font-semibold text-slate-900 dark:text-slate-100">Strava Group Tracker</p>
  </header>
</template>
