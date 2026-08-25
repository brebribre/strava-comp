<script setup lang="ts">
withDefaults(defineProps<{ title?: string; interactive?: boolean }>(), { interactive: false })
</script>

<template>
  <section
    :class="[
      // No border: the surface tint already separates a card from the page, and an outline
      // on top of that is the same signal twice.
      'rounded-lg bg-surface p-5',
      'transition-all duration-(--duration-quick) ease-(--ease-out-soft)',
      // Hover has to come from the surface instead, now that there is no edge to brighten.
      interactive ? 'cursor-pointer hover:-translate-y-px hover:bg-raised' : '',
    ]"
  >
    <header v-if="title || $slots.actions" class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 v-if="title" class="text-sm font-semibold tracking-tight text-ink">{{ title }}</h2>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
