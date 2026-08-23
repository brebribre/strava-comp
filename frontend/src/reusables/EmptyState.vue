<script setup lang="ts">
defineProps<{ title: string; hint?: string }>()
</script>

<template>
  <div class="animate-rise py-10 text-center">
    <p class="text-sm font-medium text-ink">{{ title }}</p>
    <p v-if="hint" class="mt-1 text-sm text-ink-muted">{{ hint }}</p>
    <div class="mt-4"><slot /></div>
  </div>
</template>
