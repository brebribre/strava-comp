<script setup lang="ts">
withDefaults(defineProps<{ percent: number; complete?: boolean }>(), { complete: false })
</script>

<template>
  <div class="h-1.5 w-full overflow-hidden rounded-sm bg-line">
    <div
      class="h-full rounded-sm bg-accent transition-[width] duration-(--duration-soft) ease-(--ease-out-soft)"
      :class="complete ? '' : 'opacity-60'"
      :style="{ width: `${Math.min(percent, 100)}%` }"
    />
  </div>
</template>
