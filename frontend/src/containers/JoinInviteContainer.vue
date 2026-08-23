<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useJoinInvite } from '@/hooks/useJoinInvite'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'

const route = useRoute()
const router = useRouter()
const { accept, isWorking, error } = useJoinInvite()

onMounted(async () => {
  const groupId = await accept(String(route.params.code))
  if (groupId) router.replace({ name: 'group-feed', params: { id: groupId } })
})
</script>

<template>
  <AppCard class="w-full max-w-md text-center">
    <template v-if="error">
      <p class="text-sm text-ink">{{ error }}</p>
      <AppAlert tone="error" class="mt-4">Ask whoever invited you for a fresh link.</AppAlert>
      <AppButton variant="secondary" class="mt-4" @click="router.push({ name: 'groups' })">
        Go to my groups
      </AppButton>
    </template>
    <template v-else-if="isWorking">
      <SportLoader label="Joining the group…" class="py-8" />
      <p class="-mt-4 text-sm text-ink-muted">
        You'll be asked to connect with Strava if you haven't already.
      </p>
    </template>
  </AppCard>
</template>
