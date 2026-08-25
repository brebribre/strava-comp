<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useTargetForm } from '@/hooks/useTargetForm'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'

const route = useRoute()
const groupId = () => Number(route.params.id)
const { form, exists, isLoading, isSaving, saved, error, windowError, save, remove } =
  useTargetForm(groupId)


const periods = [
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: 'year', label: 'Year' },
] as const

async function handleSave() {
  // Saving stays put now: the target lives on the Summary tab, and bouncing there would
  // interrupt someone editing the qualification rules.
  await save()
}
</script>

<template>
  <div class="max-w-2xl space-y-4">
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

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="mb-1 block text-sm font-medium text-ink">
                From
              </span>
              <input
                v-model="form.startsAt"
                type="date"
                class="w-full px-3 py-2 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
              />
              <span class="mt-1 block text-xs text-ink-muted">
                Weeks before this date don't count for or against anyone.
              </span>
            </label>

            <label class="block">
              <span class="mb-1 block text-sm font-medium text-ink">
                Until
              </span>
              <input
                v-model="form.until"
                type="date"
                class="w-full px-3 py-2 rounded-md border border-line bg-surface text-sm text-ink outline-none placeholder:text-ink-subtle transition-colors duration-(--duration-quick) focus:border-ink disabled:opacity-40"
              />
              <span class="mt-1 block text-xs text-ink-muted">
                The target stops applying after this date.
              </span>
            </label>
          </div>

          <p v-if="windowError" class="text-xs text-ink-muted">{{ windowError }}</p>
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
    </template>
  </div>
</template>
