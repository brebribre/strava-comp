<script setup lang="ts">
import type { Exercise } from '@/types/api'

defineProps<{ exercises: Exercise[] }>()
</script>

<template>
  <!-- Ordered, and repeats kept: three treadmill blocks between lifts is how the session
       actually went, and collapsing them would rewrite it. -->
  <ol class="divide-y divide-line">
    <li
      v-for="(exercise, index) in exercises"
      :key="`${exercise.name}-${index}`"
      class="flex flex-col gap-0.5 py-2 first:pt-0 last:pb-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6"
    >
      <span class="text-sm font-medium text-ink">{{ exercise.name }}</span>
      <span class="text-xs text-ink-muted sm:shrink-0 sm:text-right">
        {{ exercise.sets.join(' · ') }}
      </span>
    </li>
  </ol>
</template>
