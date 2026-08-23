<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

defineProps<{ to: RouteLocationRaw; label: string }>()
</script>

<template>
  <!-- v-slot gives isActive, so active and inactive classes are never both applied —
       otherwise conflicting utilities resolve by stylesheet order, not intent. -->
  <router-link v-slot="{ href, navigate, isActive }" :to="to" custom>
    <a
      :href="href"
      :class="[
        'relative px-1 pb-2.5 text-sm transition-colors duration-(--duration-quick)',
        isActive ? 'font-medium text-ink' : 'text-ink-subtle hover:text-ink-muted',
      ]"
      @click="navigate"
    >
      {{ label }}
      <!-- The underline scales in from the centre rather than appearing. -->
      <span
        :class="[
          'absolute inset-x-0 bottom-0 h-px origin-center bg-ink',
          'transition-transform duration-(--duration-soft) ease-(--ease-out-soft)',
          isActive ? 'scale-x-100' : 'scale-x-0',
        ]"
        aria-hidden="true"
      />
    </a>
  </router-link>
</template>
