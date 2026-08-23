<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useActivitySync } from '@/hooks/useActivitySync'
import { useFormat } from '@/hooks/useFormat'
import { useGroupSummary, WINDOW_OPTIONS } from '@/hooks/useGroupSummary'
import { TREND_METRICS, useGroupTrend } from '@/hooks/useGroupTrend'
import { useSportColors } from '@/hooks/useSportColors'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import BarChart from '@/reusables/BarChart.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import DataTable, { type Column } from '@/reusables/DataTable.vue'
import EmptyState from '@/reusables/EmptyState.vue'

const route = useRoute()
const groupId = () => Number(route.params.id)

const { members, days, isLoading, error, refresh } = useGroupSummary(groupId)
const trend = useGroupTrend(groupId, () => days.value)
const { sync, isSyncing, lastResult } = useActivitySync()
const { colorFor } = useSportColors()
const { km, duration, elevation, heartrate } = useFormat()

const columns: Column[] = [
  { key: 'name', label: 'Athlete' },
  { key: 'activity_count', label: 'Activities', align: 'right' },
  { key: 'total_distance', label: 'Distance', align: 'right' },
  { key: 'total_moving_time', label: 'Moving time', align: 'right' },
  { key: 'total_elevation_gain', label: 'Elevation', align: 'right' },
  { key: 'avg_heartrate', label: 'Avg HR', align: 'right' },
]

const hasAnyActivity = computed(() => members.value.some((m) => m.activity_count > 0))

async function handleSync() {
  if (await sync(days.value)) {
    await refresh()
    await trend.refresh()
  }
}
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <header class="flex flex-wrap items-center gap-2 sm:justify-end">
      <AppButton
        v-for="option in WINDOW_OPTIONS"
        :key="option"
        :variant="days === option ? 'primary' : 'secondary'"
        @click="days = option"
      >
        {{ option }}d
      </AppButton>
      <AppButton variant="ghost" :loading="isSyncing" @click="handleSync">Sync</AppButton>
    </header>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <AppAlert v-else-if="lastResult" tone="success">{{ lastResult }}</AppAlert>

    <AppCard title="Totals">
      <SportLoader v-if="isLoading" :size="36" />
      <EmptyState
        v-else-if="!members.length"
        title="No members yet"
        hint="Share this group's invite code to get your people in."
      />
      <DataTable v-else :columns="columns" :rows="members" row-key="athlete_id">
        <template #name="{ row }">
          <span class="font-medium">{{ row.name }}</span>
          <span v-if="row.by_sport.length" class="ml-2 hidden text-xs text-ink-subtle sm:inline">
            {{ row.by_sport.map((s: any) => s.sport_type).join(', ') }}
          </span>
        </template>
        <template #total_distance="{ row }">{{ km(row.total_distance) }}</template>
        <template #total_moving_time="{ row }">{{ duration(row.total_moving_time) }}</template>
        <template #total_elevation_gain="{ row }">{{ elevation(row.total_elevation_gain) }}</template>
        <template #avg_heartrate="{ row }">{{ heartrate(row.avg_heartrate) }}</template>
      </DataTable>
    </AppCard>

    <AppCard title="Week by week">
      <template #actions>
        <div class="flex gap-2">
          <AppButton
            v-for="option in TREND_METRICS"
            :key="option.value"
            :variant="trend.metric.value === option.value ? 'primary' : 'secondary'"
            @click="trend.metric.value = option.value"
          >
            {{ option.label }}
          </AppButton>
        </div>
      </template>

      <!-- Filters apply to both metrics: an empty selection means "everything". -->
      <div class="mb-4 space-y-2">
        <div v-if="trend.availableSports.value.length > 1" class="flex flex-wrap items-center gap-2">
          <span class="w-16 shrink-0 text-xs text-ink-subtle">Sport</span>
          <FilterChip
            v-for="sport in trend.availableSports.value"
            :key="sport"
            :label="sport"
            :color="colorFor(sport, trend.availableSports.value)"
            :active="trend.sportFilter.value.has(sport)"
            @toggle="trend.toggleSport(sport)"
          />
        </div>

        <div v-if="trend.availableAthletes.value.length > 1" class="flex flex-wrap items-center gap-2">
          <span class="w-16 shrink-0 text-xs text-ink-subtle">Athlete</span>
          <FilterChip
            v-for="person in trend.availableAthletes.value"
            :key="person.id"
            :label="person.name"
            :active="trend.athleteFilter.value.has(person.id)"
            @toggle="trend.toggleAthlete(person.id)"
          />
          <button
            v-if="trend.hasFilters.value"
            type="button"
            class="text-xs text-ink-subtle underline hover:text-ink"
            @click="trend.clearFilters()"
          >
            Clear
          </button>
        </div>
      </div>

      <SportLoader v-if="trend.isLoading.value" :size="36" />
      <EmptyState
        v-else-if="!trend.hasData.value"
        :title="trend.hasFilters.value ? 'Nothing matches these filters' : 'Nothing logged in this window'"
        :hint="
          trend.hasFilters.value
            ? 'Try clearing a filter or widening the window.'
            : hasAnyActivity
              ? 'Try a longer window.'
              : 'Activities appear here as they sync from Strava.'
        "
      />
      <BarChart v-else :data="trend.chartData.value" :options="trend.chartOptions.value" />
    </AppCard>
  </div>
</template>
