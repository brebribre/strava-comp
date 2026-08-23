<script setup lang="ts">
import SidebarContainer from '@/containers/SidebarContainer.vue'
</script>

<template>
  <!-- Layout only: the sidebar on the left, and whatever container the child route
       resolves to on the right. -->
  <div class="flex h-full bg-slate-50 dark:bg-slate-900">
    <SidebarContainer class="w-64 shrink-0" />
    <main class="flex-1 overflow-y-auto p-6">
      <router-view />
    </main>
  </div>
</template>
