<script setup lang="ts">
defineProps<{ to: { name: string; params?: Record<string, unknown> }; label: string }>()
</script>

<template>
  <!-- v-slot gives isActive, so active and inactive classes are never both applied —
       otherwise conflicting Tailwind utilities resolve by stylesheet order, not intent. -->
  <router-link v-slot="{ href, navigate, isActive }" :to="to" custom>
    <a
      :href="href"
      :class="[
        'border-b-2 px-1 pb-2 text-sm font-medium transition',
        isActive
          ? 'border-strava text-strava'
          : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200',
      ]"
      @click="navigate"
    >
      {{ label }}
    </a>
  </router-link>
</template>
