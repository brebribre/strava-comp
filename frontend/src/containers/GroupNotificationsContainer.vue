<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

import { useTelegramSettings } from '@/hooks/useTelegramSettings'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'

const route = useRoute()
const telegram = useTelegramSettings(() => Number(route.params.id))

// Only poll while someone is actually looking at the setup steps.
onMounted(() => telegram.startPolling())
onUnmounted(() => telegram.stopPolling())
</script>

<template>
  <div class="max-w-2xl space-y-4">
    <AppCard title="Telegram notifications">
      <AppAlert v-if="telegram.error.value" tone="error" class="mb-4">
        {{ telegram.error.value }}
      </AppAlert>
      <AppAlert v-else-if="telegram.notice.value" tone="success" class="mb-4">
        {{ telegram.notice.value }}
      </AppAlert>

      <!-- Connected: say which chat, and offer the two things that matter. -->
      <template v-if="telegram.isConfigured.value">
        <p class="text-sm text-ink">
          Connected to
          <strong>{{ telegram.chatTitle.value ?? 'your Telegram chat' }}</strong>.
          Every qualifying activity is posted there.
        </p>
        <div class="mt-4 flex flex-wrap gap-2">
          <AppButton
            variant="secondary"
            :loading="telegram.isTesting.value"
            @click="telegram.sendTest()"
          >
            Send test message
          </AppButton>
          <AppButton
            variant="ghost"
            :loading="telegram.isDisconnecting.value"
            @click="telegram.disconnect()"
          >
            Disconnect
          </AppButton>
        </div>
      </template>

      <!-- Not connected: three steps, no chat ids, no developer tools. -->
      <template v-else>
        <ol class="space-y-4 text-sm text-ink">
          <li class="flex gap-3">
            <span
              class="flex size-6 shrink-0 items-center justify-center rounded-sm border border-line text-xs text-ink-muted"
            >
              1
            </span>
            <span>
              Open the Telegram group you want the updates in, and add
              <strong v-if="telegram.botUsername.value">@{{ telegram.botUsername.value }}</strong>
              <strong v-else>the Bruderbande bot</strong>
              as a member.
            </span>
          </li>
          <li class="flex gap-3">
            <span
              class="flex size-6 shrink-0 items-center justify-center rounded-sm border border-line text-xs text-ink-muted"
            >
              2
            </span>
            <div class="min-w-0 flex-1">
              <p>Send this message in that group:</p>
              <div class="mt-2 flex flex-wrap items-center gap-2">
                <code
                  class="rounded-sm border border-line bg-raised px-2.5 py-1.5 text-sm tracking-wide text-ink"
                >
                  {{ telegram.connectCommand.value }}
                </code>
                <AppButton variant="secondary" @click="telegram.copyCommand()">
                  {{ telegram.copied.value ? 'Copied' : 'Copy' }}
                </AppButton>
              </div>
            </div>
          </li>
          <li class="flex gap-3">
            <span
              class="flex size-6 shrink-0 items-center justify-center rounded-sm border border-line text-xs text-ink-muted"
            >
              3
            </span>
            <span>
              The bot replies to confirm, and this page updates by itself.
            </span>
          </li>
        </ol>
        <p class="mt-4 text-xs text-ink-subtle">
          The code is specific to this group. Anyone with it can connect a chat, so only
          share it with people you'd invite here anyway.
        </p>
      </template>
    </AppCard>
  </div>
</template>
