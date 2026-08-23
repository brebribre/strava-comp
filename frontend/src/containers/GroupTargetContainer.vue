<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useGroupTarget } from '@/hooks/useGroupTarget'
import { useViewport } from '@/hooks/useViewport'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import DataTable, { type Column } from '@/reusables/DataTable.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import ProgressRing from '@/reusables/ProgressRing.vue'

const route = useRoute()
const router = useRouter()
const { athlete } = useAuth()

const { progress, me, others, hasTarget, headline, periodLabel, isLoading, error } = useGroupTarget(
  () => Number(route.params.id),
  () => athlete.value?.athlete_id,
)
const { utcDate } = useFormat()
const { isMobile } = useViewport()
const ringSize = computed(() => (isMobile.value ? 160 : 200))

const columns: Column[] = [
  { key: 'name', label: 'Athlete' },
  { key: 'completed', label: 'Done', align: 'right' },
  { key: 'remaining', label: 'To go', align: 'right' },
  { key: 'percent', label: 'Progress' },
]

function openSettings() {
  router.push({ name: 'group-settings', params: { id: route.params.id } })
}
</script>

<template>
  <div class="space-y-6">
    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <p v-else-if="isLoading" class="py-10 text-center text-sm text-slate-400">Loading target…</p>

    <EmptyState
      v-else-if="!hasTarget"
      title="No target set for this group"
      hint="Set how many exercises everyone should do each week, month or year."
    >
      <AppButton @click="openSettings">Set a target</AppButton>
    </EmptyState>

    <template v-else-if="progress && me">
      <AppAlert v-if="progress.is_expired" tone="info">
        This target ended on {{ utcDate(progress.target.until) }}.
      </AppAlert>

      <!-- The big view: where the logged-in athlete stands right now. -->
      <AppCard>
        <div class="flex flex-col items-center gap-6 py-4 sm:flex-row sm:justify-center sm:gap-12">
          <ProgressRing :percent="me.percent" :complete="me.is_complete" :size="ringSize">
            <span class="text-4xl font-bold tabular-nums text-slate-900 dark:text-slate-100">
              {{ me.completed }}<span class="text-slate-400">/{{ progress.target.count }}</span>
            </span>
            <span class="mt-1 text-xs uppercase tracking-wide text-slate-400">
              {{ periodLabel }}
            </span>
          </ProgressRing>

          <div class="text-center sm:text-left">
            <p
              class="text-2xl font-bold"
              :class="me.is_complete ? 'text-green-500' : 'text-slate-900 dark:text-slate-100'"
            >
              {{ headline }}
            </p>
            <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
              {{ progress.target.count }} exercises per {{ progress.target.period }} · target runs
              until {{ utcDate(progress.target.until) }}
            </p>
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {{ progress.days_left_in_period }} day{{
                progress.days_left_in_period === 1 ? '' : 's'
              }}
              left in this {{ progress.target.period }} ·
              {{ progress.periods_remaining }} {{ progress.target.period }}{{
                progress.periods_remaining === 1 ? '' : 's'
              }}
              remaining overall
            </p>
            <AppButton variant="ghost" class="mt-3 -ml-4" @click="openSettings">
              Edit target
            </AppButton>
          </div>
        </div>
      </AppCard>

      <AppCard title="Everyone else">
        <EmptyState
          v-if="!others.length"
          title="You're the only member"
          hint="Share the invite code to compare with your group."
        />
        <DataTable v-else :columns="columns" :rows="others" row-key="athlete_id">
          <template #name="{ row }">
            <span class="font-medium">{{ row.name }}</span>
          </template>
          <template #completed="{ row }">
            {{ row.completed }}<span class="text-slate-400">/{{ progress.target.count }}</span>
          </template>
          <template #remaining="{ row }">
            <span :class="row.is_complete ? 'text-green-500' : ''">
              {{ row.is_complete ? 'done' : row.remaining }}
            </span>
          </template>
          <template #percent="{ row }">
            <div class="flex items-center gap-3">
              <ProgressBar :percent="row.percent" :complete="row.is_complete" class="w-16 sm:w-32" />
              <span class="w-12 text-right text-xs tabular-nums text-slate-500">
                {{ Math.round(row.percent) }}%
              </span>
            </div>
          </template>
        </DataTable>
      </AppCard>
    </template>
  </div>
</template>
