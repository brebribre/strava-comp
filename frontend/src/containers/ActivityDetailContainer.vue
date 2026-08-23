<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { useActivityDetail } from '@/hooks/useActivityDetail'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppAvatar from '@/reusables/AppAvatar.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import DataTable, { type Column } from '@/reusables/DataTable.vue'
import RouteMap from '@/reusables/RouteMap.vue'
import StatRow from '@/reusables/StatRow.vue'

const route = useRoute()
const router = useRouter()

const { activity, routePath, hasRoute, isLoading, error } = useActivityDetail(() =>
  Number(route.params.activityId),
)
const { km, duration, elevation, heartrate, time, shortDate, initials, paceOrSpeed } = useFormat()

const splitColumns: Column[] = [
  { key: 'split', label: 'Km' },
  { key: 'moving_time', label: 'Time', align: 'right' },
  { key: 'elevation_difference', label: 'Elev', align: 'right' },
  { key: 'average_heartrate', label: 'HR', align: 'right' },
]

function stats() {
  const item = activity.value
  if (!item) return []
  const result = [{ label: 'Moving time', value: duration(item.moving_time) }]
  if (item.distance > 0) {
    result.unshift({ label: 'Distance', value: km(item.distance) })
    const rate = paceOrSpeed(item.sport_type, item.distance, item.moving_time)
    if (rate) result.push(rate)
  }
  result.push({ label: 'Elapsed', value: duration(item.elapsed_time) })
  if (item.total_elevation_gain > 0) {
    result.push({ label: 'Elevation', value: elevation(item.total_elevation_gain) })
  }
  if (item.average_heartrate !== null) {
    result.push({ label: 'Avg HR', value: heartrate(item.average_heartrate) })
  }
  if (item.max_heartrate !== null) {
    result.push({ label: 'Max HR', value: heartrate(item.max_heartrate) })
  }
  if (item.calories !== null) {
    result.push({ label: 'Calories', value: `${Math.round(item.calories)}` })
  }
  return result
}

function goBack() {
  router.push({ name: 'group-feed', params: { id: route.params.id } })
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <AppButton variant="ghost" @click="goBack">← Back to feed</AppButton>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <p v-else-if="isLoading" class="py-10 text-center text-sm text-ink-subtle">Loading activity…</p>

    <template v-else-if="activity">
      <AppCard>
        <header class="flex gap-3">
          <AppAvatar :initials="initials(activity.athlete_name)" :color-seed="activity.athlete_id" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-ink">
              {{ activity.athlete_name }}
            </p>
            <p class="text-xs text-ink-subtle">
              {{ shortDate(activity.start_date) }} at {{ time(activity.start_date) }}
              <span v-if="activity.device_name"> · {{ activity.device_name }}</span>
            </p>
          </div>
        </header>

        <h1 class="mt-4 text-lg font-bold text-ink">
          {{ activity.name ?? 'Untitled activity' }}
          <span
            v-if="activity.sport_type"
            class="ml-1 rounded-sm border border-line px-1.5 py-0.5 align-middle text-[11px] font-medium text-ink-muted"
          >
            {{ activity.sport_type }}
          </span>
        </h1>

        <p
          v-if="activity.description"
          class="mt-2 whitespace-pre-line text-sm text-ink"
        >
          {{ activity.description }}
        </p>
        <p v-else class="mt-2 text-sm italic text-ink-subtle">No description</p>

        <StatRow class="mt-5" :stats="stats()" />

        <AppAlert v-if="!activity.is_detailed" tone="info" class="mt-4">
          Some details couldn't be loaded from Strava — showing what we have stored.
        </AppAlert>
      </AppCard>

      <AppCard v-if="hasRoute" title="Route">
        <RouteMap :path="routePath!" class="h-72" />
      </AppCard>

      <AppCard v-if="activity.photo_url" title="Photo">
        <img :src="activity.photo_url" alt="" class="w-full rounded-lg" />
      </AppCard>

      <AppCard v-if="activity.splits.length" title="Splits">
        <DataTable :columns="splitColumns" :rows="activity.splits" row-key="split">
          <template #moving_time="{ row }">{{ duration(row.moving_time) }}</template>
          <template #elevation_difference="{ row }">
            {{ row.elevation_difference === null ? '—' : elevation(row.elevation_difference) }}
          </template>
          <template #average_heartrate="{ row }">{{ heartrate(row.average_heartrate) }}</template>
        </DataTable>
      </AppCard>
    </template>
  </div>
</template>
