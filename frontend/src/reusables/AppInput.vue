<script setup lang="ts">
defineProps<{ placeholder?: string; label?: string; disabled?: boolean }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <label class="block">
    <span v-if="label" class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
      {{ label }}
    </span>
    <input
      v-model="model"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-strava focus:ring-2 focus:ring-strava/20 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
    />
  </label>
</template>
