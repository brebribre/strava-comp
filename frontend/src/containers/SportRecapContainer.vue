<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useFormat } from '@/hooks/useFormat'
import { RECAP_METRICS, useSportRecap } from '@/hooks/useSportRecap'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import BarChart from '@/reusables/BarChart.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import LineChart from '@/reusables/LineChart.vue'
import SportIcon from '@/reusables/SportIcon.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import SportZonesContainer from '@/containers/SportZonesContainer.vue'
import StatTile from '@/reusables/StatTile.vue'

const route = useRoute()
const router = useRouter()
const months = ref(12)

const sport = computed(() => String(route.params.sport))
const {
  recap, metric, isLoading, error,
  volumeChart, volumeOptions,
  performanceChart, performanceOptions, showsPerformance,
} = useSportRecap(() => sport.value, () => months.value)

const { km, duration, elevation, heartrate, shortDate, sportLabel } = useFormat()

const windows = [
  { months: 6, label: '6 months' },
  { months: 12, label: '1 year' },
  { months: 36, label: 'All time' },
]
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <AppButton variant="ghost" @click="router.push({ name: 'recap' })">← All sports</AppButton>
      <div class="flex flex-wrap gap-2">
        <AppButton
          v-for="option in windows"
          :key="option.months"
          :variant="months === option.months ? 'primary' : 'secondary'"
          @click="months = option.months"
        >
          {{ option.label }}
        </AppButton>
      </div>
    </div>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" :label="`Reading your ${sport} history…`" class="py-12" />

    <template v-else-if="recap">
      <header class="flex items-center gap-3 sm:gap-4">
        <SportIcon :sport="recap.sport_type" :size="40" class="shrink-0 text-accent sm:size-12" />
        <div class="min-w-0">
          <PageTitle>{{ sportLabel(recap.sport_type) }}</PageTitle>
          <p class="mt-0.5 text-sm text-ink-muted">
            {{ shortDate(recap.since) }} – {{ shortDate(recap.until) }}
          </p>
        </div>
      </header>

      <EmptyState
        v-if="!recap.totals.activity_count"
        title="Nothing logged for this sport in this window"
        hint="Try a longer window."
      />

      <template v-else>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Activities" :value="String(recap.totals.activity_count)" />
          <StatTile label="Distance" :value="km(recap.totals.distance)" />
          <StatTile label="Moving time" :value="duration(recap.totals.moving_time)" />
          <StatTile label="Elevation" :value="elevation(recap.totals.elevation)" />
        </div>

        <AppCard title="Month by month">
          <template #actions>
            <div class="flex gap-2">
              <AppButton
                v-for="option in RECAP_METRICS"
                :key="option.value"
                :variant="metric === option.value ? 'primary' : 'secondary'"
                @click="metric = option.value"
              >
                {{ option.label }}
              </AppButton>
            </div>
          </template>
          <BarChart :data="volumeChart" :options="volumeOptions" />
        </AppCard>

        <AppCard v-if="showsPerformance" title="Are you getting fitter?">
          <p class="mb-4 text-sm text-ink-muted">
            Pace falling while heart rate holds steady — or drops — is the clearest sign of
            progress. The pace axis is inverted so better is always up.
          </p>
          <LineChart :data="performanceChart" :options="performanceOptions" />
        </AppCard>

        <SportZonesContainer :sport="sport" :months="months" />

        <AppCard v-if="recap.bests.length" title="Personal bests">
          <ul class="divide-y divide-line">
            <li
              v-for="best in recap.bests"
              :key="best.label"
              class="flex flex-wrap items-baseline justify-between gap-2 py-3 first:pt-0 last:pb-0"
            >
              <div class="min-w-0">
                <p class="text-sm font-medium text-ink">{{ best.label }}</p>
                <p class="truncate text-xs text-ink-subtle">
                  {{ best.activity_name ?? 'Untitled' }} · {{ shortDate(best.start_date) }}
                </p>
              </div>
              <p class="text-sm font-semibold tabular-nums text-ink">{{ best.value }}</p>
            </li>
          </ul>
        </AppCard>

        <AppCard title="Consistency">
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile
              label="Active weeks"
              :value="`${recap.consistency.active_weeks}/${recap.consistency.total_weeks}`"
            />
            <StatTile label="Longest streak" :value="`${recap.consistency.longest_streak_weeks} wks`" />
            <StatTile label="Per week" :value="String(recap.consistency.avg_per_week)" />
            <StatTile label="Biggest gap" :value="`${recap.consistency.longest_gap_days} days`" />
          </div>
        </AppCard>

        <p class="text-center text-xs text-ink-subtle">
          Average heart rate over the window: {{ heartrate(recap.totals.avg_heartrate) }}
        </p>
      </template>
    </template>
  </div>
</template>
