<script setup lang="ts">
import GroupSettingsNavContainer from '@/containers/GroupSettingsNavContainer.vue'
</script>

<template>
  <!-- Layout only: settings navigation beside whichever settings page is active. -->
  <div class="flex flex-col gap-6 sm:flex-row">
    <GroupSettingsNavContainer class="sm:w-40 sm:shrink-0" />
    <div class="min-w-0 flex-1">
      <router-view />
    </div>
  </div>
</template>
