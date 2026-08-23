<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useGroupTarget } from '@/hooks/useGroupTarget'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import TargetHeroContainer from '@/containers/TargetHeroContainer.vue'
import DataTable, { type Column } from '@/reusables/DataTable.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'

const route = useRoute()
const router = useRouter()
const { athlete } = useAuth()

const { progress, others, hasTarget, isLoading, error } = useGroupTarget(
  () => Number(route.params.id),
  () => athlete.value?.athlete_id,
)
const { utcDate } = useFormat()

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
    <SportLoader v-else-if="isLoading" label="Loading target…" />

    <EmptyState
      v-else-if="!hasTarget"
      title="No target set for this group"
      hint="Set how many exercises everyone should do each week, month or year."
    >
      <AppButton @click="openSettings">Set a target</AppButton>
    </EmptyState>

    <template v-else-if="progress">
      <AppAlert v-if="progress.is_expired" tone="info">
        This target ended on {{ utcDate(progress.target.until) }}.
      </AppAlert>

      <TargetHeroContainer show-edit />

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
            {{ row.completed }}<span class="text-ink-subtle">/{{ progress.target.count }}</span>
          </template>
          <template #remaining="{ row }">
            <span :class="row.is_complete ? 'text-ink' : ''">
              {{ row.is_complete ? 'done' : row.remaining }}
            </span>
          </template>
          <template #percent="{ row }">
            <div class="flex items-center gap-3">
              <ProgressBar :percent="row.percent" :complete="row.is_complete" class="w-16 sm:w-32" />
              <span class="w-12 text-right text-xs tabular-nums text-ink-muted">
                {{ Math.round(row.percent) }}%
              </span>
            </div>
          </template>
        </DataTable>
      </AppCard>
    </template>
  </div>
</template>
