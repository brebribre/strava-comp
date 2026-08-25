<script setup lang="ts">
import { useFormat } from '@/hooks/useFormat'
import { useSportZones } from '@/hooks/useSportZones'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import DataTable, { type Column } from '@/reusables/DataTable.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import LineChart from '@/reusables/LineChart.vue'
import SportLoader from '@/reusables/SportLoader.vue'

const props = defineProps<{ sport: string; months: number }>()

const { recap, hasZones, hasTrend, paceChart, paceOptions, isLoading, error } = useSportZones(
  () => props.sport,
  () => props.months,
)
const { km, pace } = useFormat()

const columns: Column[] = [
  { key: 'label', label: 'Zone' },
  { key: 'activity_count', label: 'Runs', align: 'right' },
  { key: 'distance', label: 'Distance', align: 'right' },
  { key: 'avg_pace_seconds_per_km', label: 'Pace', align: 'right' },
  { key: 'pace_delta_seconds', label: 'vs previous', align: 'right' },
]

/** Negative delta means fewer seconds per kilometre — faster at the same effort. */
function deltaLabel(seconds: number | null): string {
  if (seconds === null) return '—'
  if (Math.abs(seconds) < 1) return 'no change'
  return `${Math.abs(Math.round(seconds))}s ${seconds < 0 ? 'faster' : 'slower'}`
}
</script>

<template>
  <AppCard title="By effort zone">
    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" :size="36" class="py-6" />

    <EmptyState
      v-else-if="!hasZones"
      title="No heart-rate data for this sport"
      hint="Zones are worked out from average heart rate, so runs without it can't be classified."
    />

    <template v-else-if="recap">
      <p class="mb-4 text-sm text-ink-muted">
        Grouped by average heart rate against an estimated max of
        <strong>{{ recap.hr_max }} bpm</strong> ({{ recap.hr_max_basis }}).
        <strong>Getting faster at the same zone is the improvement</strong> — the pace column
        compares with the previous {{ months }} months.
      </p>

      <DataTable :columns="columns" :rows="recap.zones" row-key="zone">
        <template #label="{ row }">
          <span class="font-medium">Z{{ row.zone }} {{ row.label }}</span>
          <span class="ml-2 text-xs text-ink-subtle">{{ row.low_bpm }}–{{ row.high_bpm }} bpm</span>
        </template>
        <template #distance="{ row }">{{ km(row.distance) }}</template>
        <template #avg_pace_seconds_per_km="{ row }">
          {{ pace(row.avg_pace_seconds_per_km) }}
        </template>
        <template #pace_delta_seconds="{ row }">
          <span :class="row.pace_delta_seconds !== null && row.pace_delta_seconds < 0 ? 'font-semibold text-ink' : 'text-ink-muted'">
            {{ deltaLabel(row.pace_delta_seconds) }}
          </span>
        </template>
      </DataTable>

      <p v-if="recap.unclassified_count" class="mt-3 text-xs text-ink-subtle">
        {{ recap.unclassified_count }} activit{{ recap.unclassified_count === 1 ? 'y' : 'ies' }}
        had no heart rate and aren't counted here.
      </p>

      <template v-if="hasTrend">
        <h3 class="mt-6 mb-3 text-sm font-semibold text-ink">Pace within each zone</h3>
        <LineChart :data="paceChart" :options="paceOptions" />
      </template>
    </template>
  </AppCard>
</template>
