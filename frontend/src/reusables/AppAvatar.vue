<script setup lang="ts">
defineProps<{ initials: string; colorSeed?: number }>()

// Deterministic colour per person, so the same athlete always looks the same.
const palette = [
  'bg-orange-500',
  'bg-blue-500',
  'bg-green-600',
  'bg-purple-500',
  'bg-red-500',
  'bg-cyan-600',
]
</script>

<template>
  <span
    :class="[
      'inline-flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white',
      palette[(colorSeed ?? 0) % palette.length],
    ]"
  >
    {{ initials }}
  </span>
</template>
