<script setup lang="ts">
defineProps<{ placeholder?: string; label?: string; disabled?: boolean }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <label class="block">
    <span v-if="label" class="mb-1.5 block text-xs font-medium text-ink-muted">{{ label }}</span>
    <input
      v-model="model"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-subtle disabled:opacity-40 transition-colors duration-(--duration-quick) focus:border-ink"
    />
  </label>
</template>
