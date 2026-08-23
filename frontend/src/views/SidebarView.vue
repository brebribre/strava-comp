<script setup lang="ts">
import MobileTopBarContainer from '@/containers/MobileTopBarContainer.vue'
import SidebarContainer from '@/containers/SidebarContainer.vue'
</script>

<template>
  <!-- Layout only: sidebar (a drawer below lg) plus whatever the child route resolves to. -->
  <div class="flex h-full bg-canvas">
    <SidebarContainer />

    <div class="flex min-w-0 flex-1 flex-col">
      <MobileTopBarContainer class="lg:hidden" />
      <main class="flex-1 overflow-y-auto p-4 sm:p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
