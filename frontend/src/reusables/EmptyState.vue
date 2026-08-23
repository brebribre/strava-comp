<script setup lang="ts">
defineProps<{ title: string; hint?: string }>()
</script>

<template>
  <div class="py-10 text-center">
    <p class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ title }}</p>
    <p v-if="hint" class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ hint }}</p>
    <div class="mt-4"><slot /></div>
  </div>
</template>
