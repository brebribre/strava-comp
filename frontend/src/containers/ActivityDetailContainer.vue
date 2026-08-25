<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { ref } from 'vue'

import { useActivityDetail } from '@/hooks/useActivityDetail'
import { useShareCard } from '@/hooks/useShareCard'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppAvatar from '@/reusables/AppAvatar.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import DataTable, { type Column } from '@/reusables/DataTable.vue'
import AppModal from '@/reusables/AppModal.vue'
import RouteMap from '@/reusables/RouteMap.vue'
import SportIcon from '@/reusables/SportIcon.vue'
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

const shareCard = useShareCard()
const isShareOpen = ref(false)

async function openShare() {
  if (!activity.value) return
  isShareOpen.value = true
  await shareCard.preview(activity.value)
}

function closeShare() {
  isShareOpen.value = false
  shareCard.clear()
}

function goBack() {
  router.push({ name: 'group-feed', params: { id: route.params.id } })
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <div class="flex items-center justify-between gap-2">
      <AppButton variant="ghost" @click="goBack">← Back to feed</AppButton>
      <AppButton v-if="activity" variant="secondary" @click="openShare">Share</AppButton>
    </div>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" label="Loading activity…" class="py-12" />

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

        <h1 class="mt-4 text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          {{ activity.name ?? 'Untitled activity' }}
          <span
            v-if="activity.sport_type"
            class="ml-1 inline-flex items-center gap-1 rounded-sm border border-line px-1.5 py-0.5 align-middle text-[11px] font-medium text-ink-muted"
          >
            <SportIcon :sport="activity.sport_type" :size="14" class="text-accent" />
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

    <AppModal v-if="isShareOpen && activity" title="Share this activity" @close="closeShare">
      <SportLoader v-if="shareCard.isWorking.value" :size="36" class="py-8" />
      <AppAlert v-else-if="shareCard.error.value" tone="error">
        {{ shareCard.error.value }}
      </AppAlert>
      <template v-else-if="shareCard.previewUrl.value">
        <img
          :src="shareCard.previewUrl.value"
          alt="Shareable summary of this activity"
          class="w-full rounded-md border border-line"
        />
        <div class="mt-4 flex flex-wrap gap-2">
          <AppButton
            v-if="shareCard.canShareFiles(activity)"
            @click="shareCard.share(activity)"
          >
            Share…
          </AppButton>
          <AppButton variant="secondary" @click="shareCard.download(activity)">
            Save image
          </AppButton>
        </div>
      </template>
    </AppModal>
  </div>
</template>
