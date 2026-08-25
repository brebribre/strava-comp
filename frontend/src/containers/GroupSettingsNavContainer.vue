<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const items = [
  { name: 'group-settings-members', label: 'Members' },
  { name: 'group-settings-target', label: 'Target' },
  { name: 'group-settings-notifications', label: 'Notifications' },
]
</script>

<template>
  <nav class="flex gap-1 overflow-x-auto sm:flex-col sm:gap-0.5">
    <router-link
      v-for="item in items"
      :key="item.name"
      :to="{ name: item.name, params: { id: route.params.id } }"
      v-slot="{ href, navigate, isActive }"
      custom
    >
      <a
        :href="href"
        :class="[
          'whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors duration-(--duration-quick)',
          isActive
            ? 'bg-accent-soft font-medium text-accent'
            : 'text-ink-muted hover:bg-raised hover:text-ink',
        ]"
        @click="navigate"
      >
        {{ item.label }}
      </a>
    </router-link>
  </nav>
</template>
