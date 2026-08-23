<script setup lang="ts">
withDefaults(
  defineProps<{ size?: 'sm' | 'md' | 'lg'; subtitle?: string; align?: 'left' | 'center' }>(),
  { size: 'md', align: 'left' },
)

// Wider than tall: heavy weight, uppercase, generous tracking, and a horizontal stretch.
// Sizes are deliberately small in text terms — the width comes from the treatment.
const sizes = {
  sm: 'text-[13px]',
  md: 'text-[17px]',
  lg: 'text-[30px]',
}
</script>

<template>
  <div class="select-none">
    <span
      :class="[
        'block font-extrabold uppercase leading-none tracking-[0.18em] text-ink',
        sizes[size],
      ]"
      :style="{
        transform: 'scaleX(1.12)',
        // The stretch grows from the origin, so a left-anchored logo would drift right of
        // centre when its parent centres it.
        transformOrigin: align === 'center' ? 'center' : 'left center',
      }"
    >
      Bruderbande
    </span>
    <span
      v-if="subtitle"
      class="mt-1.5 block text-[11px] uppercase tracking-[0.14em] text-ink-subtle"
    >
      {{ subtitle }}
    </span>
  </div>
</template>
