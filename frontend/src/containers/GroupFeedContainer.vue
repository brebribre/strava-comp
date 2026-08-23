<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { useFormat } from '@/hooks/useFormat'
import { useGroupFeed } from '@/hooks/useGroupFeed'
import AppAlert from '@/reusables/AppAlert.vue'
import AppAvatar from '@/reusables/AppAvatar.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import RouteMap from '@/reusables/RouteMap.vue'
import StatRow from '@/reusables/StatRow.vue'

const route = useRoute()
const router = useRouter()
const groupId = () => Number(route.params.id)

const { days, isLoading, isLoadingMore, hasMore, error, loadMore } = useGroupFeed(groupId)
const { km, duration, elevation, heartrate, time, initials, paceOrSpeed } = useFormat()

function openActivity(activityId: number) {
  router.push({ name: 'activity', params: { id: route.params.id, activityId } })
}

function statsFor(item: {
  sport_type: string | null
  distance: number
  moving_time: number
  total_elevation_gain: number
  average_heartrate: number | null
}) {
  const stats = [{ label: 'Time', value: duration(item.moving_time) }]
  if (item.distance > 0) {
    stats.unshift({ label: 'Distance', value: km(item.distance) })
    const rate = paceOrSpeed(item.sport_type, item.distance, item.moving_time)
    if (rate) stats.push(rate)
  }
  if (item.total_elevation_gain > 0) {
    stats.push({ label: 'Elevation', value: elevation(item.total_elevation_gain) })
  }
  if (item.average_heartrate !== null) {
    stats.push({ label: 'Avg HR', value: heartrate(item.average_heartrate) })
  }
  return stats
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>

    <p v-if="isLoading" class="py-10 text-center text-sm text-slate-400">Loading feed…</p>

    <EmptyState
      v-else-if="!days.length"
      title="Nothing here yet"
      hint="Activities appear as soon as anyone in the group finishes one."
    />

    <template v-else>
      <section v-for="day in days" :key="day.label" class="space-y-3">
        <h2 class="pt-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          {{ day.label }}
        </h2>

        <AppCard
          v-for="entry in day.entries"
          :key="entry.item.activity_id"
          class="cursor-pointer transition hover:border-slate-300 dark:hover:border-slate-600"
          @click="openActivity(entry.item.activity_id)"
        >
          <article class="flex gap-3">
            <AppAvatar
              :initials="initials(entry.item.athlete_name)"
              :color-seed="entry.item.athlete_id"
            />
            <div class="min-w-0 flex-1">
              <header class="flex items-baseline justify-between gap-2">
                <p class="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {{ entry.item.athlete_name }}
                </p>
                <time class="shrink-0 text-xs text-slate-400">{{
                  time(entry.item.start_date)
                }}</time>
              </header>

              <p class="mt-0.5 truncate text-sm text-slate-700 dark:text-slate-300">
                {{ entry.item.name ?? 'Untitled activity' }}
                <span
                  v-if="entry.item.sport_type"
                  class="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                >
                  {{ entry.item.sport_type }}
                </span>
              </p>

              <StatRow class="mt-3" :stats="statsFor(entry.item)" />
            </div>
          </article>

          <!-- Photo when Strava has one, otherwise the GPS trace. Indoor activities have
               neither, so the card simply stays compact. -->
          <img
            v-if="entry.item.photo_url"
            :src="entry.item.photo_url"
            alt=""
            class="mt-4 max-h-64 w-full rounded-lg object-cover"
          />
          <RouteMap
            v-else-if="entry.routePath"
            :path="entry.routePath"
            :width="640"
            :height="200"
            class="mt-4 h-40"
          />
        </AppCard>
      </section>

      <div v-if="hasMore" class="pt-2 text-center">
        <AppButton variant="secondary" :loading="isLoadingMore" @click="loadMore">
          Load older activities
        </AppButton>
      </div>
    </template>
  </div>
</template>
