<script setup lang="ts">
defineProps<{ label: string; value: string; delta?: number | null; hint?: string }>()
</script>

<template>
  <div class="rounded-md bg-raised p-4">
    <p class="text-[11px] uppercase tracking-wide text-ink-subtle">{{ label }}</p>
    <p class="mt-1 text-2xl font-bold tabular-nums text-ink">{{ value }}</p>
    <p v-if="delta !== null && delta !== undefined" class="mt-1 text-xs tabular-nums text-ink-muted">
      <!-- Monochrome, so direction is carried by the arrow rather than red/green. -->
      {{ delta > 0 ? '↑' : delta < 0 ? '↓' : '→' }} {{ Math.abs(delta).toFixed(0) }}% vs previous
    </p>
    <p v-else-if="hint" class="mt-1 text-xs text-ink-subtle">{{ hint }}</p>
  </div>
</template>
