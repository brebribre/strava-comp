<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ path: string; width?: number; height?: number }>()

// A path with many segments is a court/lap activity, not a point-to-point route.
const dense = computed(() => (props.path.match(/L/g)?.length ?? 0) > 300)
</script>

<template>
  <!-- No tile layer: this is the GPS trace itself, drawn as an SVG path. Keeps the bundle
       free of a map library and inherits the monochrome palette. -->
  <svg
    :viewBox="`0 0 ${width ?? 600} ${height ?? 320}`"
    class="h-full w-full rounded-md bg-raised text-accent"
    preserveAspectRatio="xMidYMid meet"
  >
    <!-- Semi-transparent so repeated passes over the same ground accumulate and read as
         density — which is what makes a court sport look like a heatmap. -->
    <path
      :d="path"
      fill="none"
      stroke="currentColor"
      :stroke-width="dense ? 1.5 : 2.5"
      :stroke-opacity="dense ? 0.4 : 0.85"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>
