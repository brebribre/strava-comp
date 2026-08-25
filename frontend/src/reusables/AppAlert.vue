<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'error' | 'info' | 'success' }>(), { tone: 'error' })

// Monochrome: tone is carried by the weight of the left rule and the text, not by colour.
const tones = {
  error: 'border-l-ink text-ink',
  info: 'border-l-line-strong text-ink-muted',
  success: 'border-l-ink text-ink',
}
</script>

<template>
  <p
    :class="[
      'animate-rise rounded-md border-l-2 bg-raised px-3 py-2 text-sm',
      tones[tone],
    ]"
  >
    <slot />
  </p>
</template>
