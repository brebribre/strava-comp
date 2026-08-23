<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useTargetForm } from '@/hooks/useTargetForm'
import { useTelegramSettings } from '@/hooks/useTelegramSettings'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'

const route = useRoute()
const router = useRouter()
const groupId = () => Number(route.params.id)
const { form, exists, isLoading, isSaving, saved, error, save, remove } = useTargetForm(groupId)
const telegram = useTelegramSettings(groupId)

// Only poll while someone is actually looking at the setup steps.
onMounted(() => telegram.startPolling())
onUnmounted(() => telegram.stopPolling())

const periods = [
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: 'year', label: 'Year' },
] as const

async function handleSave() {
  if (await save()) {
    router.push({ name: 'group-target', params: { id: route.params.id } })
  }
}
</script>

<template>
  <div class="max-w-2xl space-y-6">
    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <AppAlert v-else-if="saved" tone="success">Target saved.</AppAlert>
    <SportLoader v-if="isLoading" :size="36" class="py-6" />

    <template v-else>
      <AppCard title="Target">
        <div class="space-y-4">
          <div class="flex flex-wrap items-end gap-4">
            <label class="block">
              <span class="mb-1 block text-sm font-medium text-ink">
                How many exercises
              </span>
              <input
                v-model.number="form.count"
                type="number"
                min="1"
                max="100"
                class="w-28 px-3 py-2 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
              />
            </label>

            <div>
              <span class="mb-1 block text-sm font-medium text-ink">
                per
              </span>
              <div class="flex gap-2">
                <AppButton
                  v-for="option in periods"
                  :key="option.value"
                  :variant="form.period === option.value ? 'primary' : 'secondary'"
                  @click="form.period = option.value"
                >
                  {{ option.label }}
                </AppButton>
              </div>
            </div>
          </div>

          <label class="block">
            <span class="mb-1 block text-sm font-medium text-ink">
              Until
            </span>
            <input
              v-model="form.until"
              type="date"
              class="px-3 py-2 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
            />
            <span class="mt-1 block text-xs text-ink-muted">
              The target stops applying after this date.
            </span>
          </label>
        </div>
      </AppCard>

      <AppCard title="What counts as an exercise">
        <p class="mb-4 text-sm text-ink-muted">
          An activity counts when it meets the rule for its sport. Where both time and distance
          are set, <strong>either one</strong> is enough.
        </p>

        <div class="space-y-3">
          <div
            v-for="row in form.sports"
            :key="row.sport"
            class="flex flex-wrap items-center gap-3 rounded-lg border border-line p-3"
          >
            <label class="flex w-40 items-center gap-2">
              <input
                v-model="row.enabled"
                type="checkbox"
                class="size-4 rounded border-line accent-ink"
              />
              <span class="text-sm font-medium text-ink">
                {{ row.sport }}
              </span>
            </label>

            <label class="flex items-center gap-2 text-sm text-ink-muted">
              at least
              <input
                v-model.number="row.minMinutes"
                type="number"
                min="1"
                :disabled="!row.enabled"
                class="w-20 px-2 py-1 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
              />
              min
            </label>

            <label class="flex items-center gap-2 text-sm text-ink-muted">
              or
              <input
                v-model.number="row.minDistanceKm"
                type="number"
                min="0"
                step="0.5"
                :disabled="!row.enabled"
                placeholder="—"
                class="w-20 px-2 py-1 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
              />
              km
            </label>
          </div>

          <div class="rounded-lg border border-dashed border-line p-3">
            <label class="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
              <span class="w-40 font-medium text-ink">Any other sport</span>
              at least
              <input
                v-model.number="form.defaultMinMinutes"
                type="number"
                min="1"
                class="w-20 px-2 py-1 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
              />
              min
            </label>
          </div>
        </div>
      </AppCard>

      <div class="flex items-center gap-3">
        <AppButton :loading="isSaving" @click="handleSave">
          {{ exists ? 'Save target' : 'Create target' }}
        </AppButton>
        <AppButton v-if="exists" variant="ghost" :loading="isSaving" @click="remove">
          Remove target
        </AppButton>
      </div>

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
    </template>
  </div>
</template>
