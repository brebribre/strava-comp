<script setup lang="ts">
defineProps<{ stats: { label: string; value: string }[] }>()
</script>

<template>
  <dl class="flex flex-wrap gap-x-8 gap-y-2">
    <div v-for="stat in stats" :key="stat.label">
      <dt class="text-xs text-slate-500 dark:text-slate-400">{{ stat.label }}</dt>
      <dd class="text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
        {{ stat.value }}
      </dd>
    </div>
  </dl>
</template>
