<script setup lang="ts">
import GroupHeaderContainer from '@/containers/GroupHeaderContainer.vue'
</script>

<template>
  <!-- Layout only: group header + tabs, with the active tab's container rendered
       through the nested router-view. -->
  <div class="mx-auto max-w-5xl">
    <GroupHeaderContainer />
    <router-view />
  </div>
</template>
