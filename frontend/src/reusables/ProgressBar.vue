<script setup lang="ts">
withDefaults(defineProps<{ percent: number; complete?: boolean }>(), { complete: false })
</script>

<template>
  <div class="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
    <div
      class="h-full rounded-full transition-[width] duration-700"
      :class="complete ? 'bg-green-500' : 'bg-strava'"
      :style="{ width: `${Math.min(percent, 100)}%` }"
    />
  </div>
</template>
