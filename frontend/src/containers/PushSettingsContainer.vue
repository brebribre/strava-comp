<script setup lang="ts">
import { onMounted } from 'vue'

import { usePushNotifications } from '@/hooks/usePushNotifications'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import PageTitle from '@/reusables/PageTitle.vue'

const {
  isSupported,
  serverEnabled,
  isSubscribed,
  isBusy,
  isBlocked,
  needsInstall,
  error,
  message,
  refresh,
  enable,
  disable,
  sendTest,
} = usePushNotifications()

onMounted(refresh)
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <PageTitle>Notifications</PageTitle>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <AppAlert v-else-if="message" tone="success">{{ message }}</AppAlert>

    <AppCard title="This device">
      <p class="mb-4 text-sm text-ink-muted">
        A notification arrives whenever anyone in your groups finishes a workout — yourself
        included, which is how you know it is working.
      </p>

      <!-- The iPhone case, spelled out: Safari has no Push API in a tab, so the button
           below cannot work until the app is on the Home Screen. -->
      <AppAlert v-if="needsInstall" tone="info" class="mb-4">
        On iPhone this works only once Bruderbande is on your Home Screen. Tap
        <strong>Share</strong> in Safari, then <strong>Add to Home Screen</strong>, open it
        from there, and come back to this page.
      </AppAlert>

      <AppAlert v-else-if="!isSupported" tone="info" class="mb-4">
        This browser has no support for push notifications.
      </AppAlert>

      <AppAlert v-else-if="!serverEnabled" tone="info" class="mb-4">
        Push is not configured on the server yet.
      </AppAlert>

      <AppAlert v-else-if="isBlocked" tone="info" class="mb-4">
        Notifications are blocked for this app. Turn them back on in your device settings,
        then reload this page.
      </AppAlert>

      <div class="flex flex-wrap items-center gap-2">
        <AppButton
          v-if="!isSubscribed"
          :loading="isBusy"
          :disabled="!isSupported || !serverEnabled || needsInstall || isBlocked"
          @click="enable"
        >
          Turn on notifications
        </AppButton>

        <template v-else>
          <AppButton variant="secondary" :loading="isBusy" @click="sendTest">
            Send a test
          </AppButton>
          <AppButton variant="ghost" :loading="isBusy" @click="disable">
            Turn off on this device
          </AppButton>
        </template>
      </div>

      <p v-if="isSubscribed" class="mt-3 text-xs text-ink-subtle">
        This device is subscribed. Each phone or browser has to be turned on separately.
      </p>
    </AppCard>
  </div>
</template>
