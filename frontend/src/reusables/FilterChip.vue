<script setup lang="ts">
withDefaults(defineProps<{ label: string; active?: boolean; color?: string }>(), {
  active: false,
})

defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    type="button"
    :class="[
      'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition',
      active
        ? 'border-transparent bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
        : 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800',
    ]"
    @click="$emit('toggle')"
  >
    <span
      v-if="color"
      class="size-2 rounded-full"
      :style="{ backgroundColor: color }"
      aria-hidden="true"
    />
    {{ label }}
  </button>
</template>
