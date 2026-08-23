<script setup lang="ts">
withDefaults(defineProps<{ title?: string; interactive?: boolean }>(), { interactive: false })
</script>

<template>
  <section
    :class="[
      'rounded-lg border border-line bg-surface p-5',
      'transition-all duration-(--duration-quick) ease-(--ease-out-soft)',
      interactive ? 'cursor-pointer hover:-translate-y-px hover:border-line-strong' : '',
    ]"
  >
    <header v-if="title || $slots.actions" class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 v-if="title" class="text-sm font-semibold tracking-tight text-ink">{{ title }}</h2>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
