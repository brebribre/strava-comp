<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'error' | 'info' | 'success' }>(), { tone: 'error' })

const tones = {
  error: 'bg-red-50 text-red-700 ring-red-200 dark:bg-red-950 dark:text-red-200 dark:ring-red-900',
  info: 'bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-950 dark:text-blue-200 dark:ring-blue-900',
  success:
    'bg-green-50 text-green-700 ring-green-200 dark:bg-green-950 dark:text-green-200 dark:ring-green-900',
}
</script>

<template>
  <p :class="['rounded-lg px-3 py-2 text-sm ring-1', tones[tone]]"><slot /></p>
</template>
