<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useFormat } from '@/hooks/useFormat'
import { useRecap, RECAP_WINDOWS } from '@/hooks/useRecap'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import SportIcon from '@/reusables/SportIcon.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import StatTile from '@/reusables/StatTile.vue'

const router = useRouter()
const { overview, sports, days, hasData, showsGrowth, totalGrowth, isLoading, error } = useRecap()
const { km, duration, heartrate, utcDate } = useFormat()

function openSport(sport: string) {
  router.push({ name: 'recap-sport', params: { sport } })
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-ink">Recap</h1>
        <p class="mt-1 text-sm text-ink-muted">How each sport has grown. Just yours.</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <AppButton
          v-for="option in RECAP_WINDOWS"
          :key="option.days"
          :variant="days === option.days ? 'primary' : 'secondary'"
          @click="days = option.days"
        >
          {{ option.label }}
        </AppButton>
      </div>
    </header>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" label="Building your recap…" class="py-12" />

    <EmptyState
      v-else-if="!hasData"
      title="Nothing in this window"
      hint="Try a longer window, or sync more history from the Summary tab of a group."
    />

    <template v-else-if="overview">
      <AppCard title="Everything together">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Activities"
            :value="String(overview.total.activity_count)"
            :delta="totalGrowth.activity_count"
          />
          <StatTile
            label="Distance"
            :value="km(overview.total.distance)"
            :delta="totalGrowth.distance"
          />
          <StatTile
            label="Moving time"
            :value="duration(overview.total.moving_time)"
            :delta="totalGrowth.moving_time"
          />
          <StatTile label="Avg HR" :value="heartrate(overview.total.avg_heartrate)" />
        </div>
        <p class="mt-3 text-xs text-ink-subtle">
          {{ utcDate(overview.since) }} – {{ utcDate(overview.until) }}
          <template v-if="showsGrowth"> · compared with the {{ overview.days }} days before</template>
          <template v-else-if="overview.first_activity">
            · no comparison shown — your history starts
            {{ utcDate(overview.first_activity) }}, so the previous period isn't covered
          </template>
        </p>
      </AppCard>

      <div class="grid gap-4 sm:grid-cols-2">
        <AppCard
          v-for="sport in sports"
          :key="sport.sport_type"
          interactive
          class="animate-rise"
          @click="openSport(sport.sport_type)"
        >
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <SportIcon :sport="sport.sport_type" :size="20" class="text-accent" />
              <h2 class="text-sm font-semibold text-ink">{{ sport.sport_type }}</h2>
            </div>
            <span class="text-xs text-ink-subtle">{{ sport.current.activity_count }} activities</span>
          </div>

          <div class="mt-4 grid grid-cols-2 gap-3">
            <StatTile
              label="Distance"
              :value="km(sport.current.distance)"
              :delta="sport.growth_distance"
              hint="no earlier data"
            />
            <StatTile
              label="Time"
              :value="duration(sport.current.moving_time)"
              :delta="sport.growth_moving_time"
              hint="no earlier data"
            />
          </div>
        </AppCard>
      </div>
    </template>
  </div>
</template>
