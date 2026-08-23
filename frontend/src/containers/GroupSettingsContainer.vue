<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { useTargetForm } from '@/hooks/useTargetForm'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'

const route = useRoute()
const router = useRouter()
const { form, exists, isLoading, isSaving, saved, error, save, remove } = useTargetForm(
  () => Number(route.params.id),
)

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
    <p v-if="isLoading" class="text-sm text-slate-400">Loading…</p>

    <template v-else>
      <AppCard title="Target">
        <div class="space-y-4">
          <div class="flex flex-wrap items-end gap-4">
            <label class="block">
              <span class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                How many exercises
              </span>
              <input
                v-model.number="form.count"
                type="number"
                min="1"
                max="100"
                class="w-28 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-strava focus:ring-2 focus:ring-strava/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
            </label>

            <div>
              <span class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
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
            <span class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Until
            </span>
            <input
              v-model="form.until"
              type="date"
              class="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-strava focus:ring-2 focus:ring-strava/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            <span class="mt-1 block text-xs text-slate-500 dark:text-slate-400">
              The target stops applying after this date.
            </span>
          </label>
        </div>
      </AppCard>

      <AppCard title="What counts as an exercise">
        <p class="mb-4 text-sm text-slate-500 dark:text-slate-400">
          An activity counts when it meets the rule for its sport. Where both time and distance
          are set, <strong>either one</strong> is enough.
        </p>

        <div class="space-y-3">
          <div
            v-for="row in form.sports"
            :key="row.sport"
            class="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700"
          >
            <label class="flex w-40 items-center gap-2">
              <input
                v-model="row.enabled"
                type="checkbox"
                class="size-4 rounded border-slate-300 text-strava focus:ring-strava"
              />
              <span class="text-sm font-medium text-slate-900 dark:text-slate-100">
                {{ row.sport }}
              </span>
            </label>

            <label class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              at least
              <input
                v-model.number="row.minMinutes"
                type="number"
                min="1"
                :disabled="!row.enabled"
                class="w-20 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 disabled:opacity-40 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
              min
            </label>

            <label class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              or
              <input
                v-model.number="row.minDistanceKm"
                type="number"
                min="0"
                step="0.5"
                :disabled="!row.enabled"
                placeholder="—"
                class="w-20 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 disabled:opacity-40 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              />
              km
            </label>
          </div>

          <div class="rounded-lg border border-dashed border-slate-300 p-3 dark:border-slate-600">
            <label class="flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              <span class="w-40 font-medium text-slate-900 dark:text-slate-100">Any other sport</span>
              at least
              <input
                v-model.number="form.defaultMinMinutes"
                type="number"
                min="1"
                class="w-20 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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
