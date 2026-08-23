<script setup lang="ts">
defineProps<{ stats: { label: string; value: string }[] }>()
</script>

<template>
  <dl class="flex flex-wrap gap-x-7 gap-y-2">
    <div v-for="stat in stats" :key="stat.label">
      <dt class="text-[11px] uppercase tracking-wide text-ink-subtle">{{ stat.label }}</dt>
      <dd class="text-sm font-semibold tabular-nums text-ink">{{ stat.value }}</dd>
    </div>
  </dl>
</template>
