<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ percent: number; size?: number; stroke?: number; complete?: boolean }>(),
  { size: 200, stroke: 14, complete: false },
)

const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
// The dash gap is what "unfilled" means on a ring.
const offset = computed(() => circumference.value * (1 - Math.min(props.percent, 100) / 100))
</script>

<template>
  <div class="relative" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" class="-rotate-90">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :stroke-width="stroke"
        class="stroke-slate-200 dark:stroke-slate-700"
      />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        :class="complete ? 'stroke-green-500' : 'stroke-strava'"
        class="transition-[stroke-dashoffset] duration-700"
      />
    </svg>
    <div class="absolute inset-0 flex flex-col items-center justify-center">
      <slot />
    </div>
  </div>
</template>
