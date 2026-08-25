<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useTargetHistory } from '@/hooks/useTargetHistory'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import SportLoader from '@/reusables/SportLoader.vue'

const route = useRoute()
const { rows, targetCount, weeksHit, hasTarget, isLoading, error } = useTargetHistory(
  () => Number(route.params.id),
)
</script>

<template>
  <AppCard v-if="hasTarget" title="Week by week">
    <template #actions>
      <span class="text-xs text-ink-subtle">
        {{ weeksHit }} of {{ rows.length }} weeks hit · target {{ targetCount }}/week
      </span>
    </template>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" :size="36" class="py-6" />

    <ul v-else class="divide-y divide-line">
      <li
        v-for="row in rows"
        :key="row.key"
        class="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5 first:pt-0 last:pb-0"
      >
        <span
          class="w-32 shrink-0 text-xs"
          :class="row.isCurrent ? 'font-medium text-ink' : 'text-ink-muted'"
        >
          {{ row.label }}
        </span>

        <ProgressBar
          v-if="row.mine"
          :percent="row.mine.percent"
          :complete="row.mine.isComplete"
          class="min-w-24 flex-1"
        />

        <span class="w-12 shrink-0 text-right text-xs tabular-nums text-ink">
          {{ row.mine?.completed ?? 0 }}/{{ row.targetCount }}
        </span>

        <!-- Everyone else, compact: enough to see who showed up that week. -->
        <span v-if="row.others.length" class="w-full text-xs text-ink-subtle sm:w-auto">
          <span v-for="other in row.others" :key="other.athlete_id" class="mr-3">
            {{ other.name.split(' ')[0] }}
            <span :class="other.is_complete ? 'font-medium text-ink' : ''">
              {{ other.completed }}/{{ row.targetCount }}
            </span>
          </span>
        </span>
      </li>
    </ul>
  </AppCard>
</template>
