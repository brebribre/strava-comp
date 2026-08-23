<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useLoginError } from '@/hooks/useLoginError'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppLogo from '@/reusables/AppLogo.vue'
import AppCard from '@/reusables/AppCard.vue'

const route = useRoute()
const { login } = useAuth()
const { message } = useLoginError(
  () => (route.query.error ?? route.query.invite_error) as string | undefined,
)
</script>

<template>
  <AppCard class="w-full max-w-md">
    <div class="text-center">
      <AppLogo size="lg" align="center" />
      <p class="mt-3 text-sm text-ink-muted">Compare training with your group.</p>

      <AppAlert v-if="message" tone="error" class="mt-4">{{ message }}</AppAlert>

      <AppButton class="mt-6 w-full" @click="login()">Connect with Strava</AppButton>
    </div>
  </AppCard>
</template>
