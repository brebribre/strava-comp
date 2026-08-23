<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<template>
  <section
    class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800"
  >
    <header v-if="title || $slots.actions" class="mb-4 flex items-center justify-between gap-4">
      <h2 v-if="title" class="text-base font-semibold text-slate-900 dark:text-slate-100">
        {{ title }}
      </h2>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
