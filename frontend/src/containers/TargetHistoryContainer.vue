<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useTargetHistory } from '@/hooks/useTargetHistory'
import AppAlert from '@/reusables/AppAlert.vue'
import AppAvatar from '@/reusables/AppAvatar.vue'
import AppCard from '@/reusables/AppCard.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import { useFormat } from '@/hooks/useFormat'

const route = useRoute()
const { rows, targetCount, weeksCounted, hasTarget, isLoading, error } = useTargetHistory(
  () => Number(route.params.id),
)
const { initials } = useFormat()
</script>

<template>
  <AppCard v-if="hasTarget" title="Weekly record">
    <template #actions>
      <span class="text-xs text-ink-subtle">
        last {{ weeksCounted }} weeks · target {{ targetCount }}/week
      </span>
    </template>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" :size="36" class="py-6" />

    <ul v-else class="divide-y divide-line">
      <li
        v-for="row in rows"
        :key="row.athlete_id"
        class="flex flex-wrap items-center gap-x-4 gap-y-2 py-3 first:pt-0 last:pb-0"
      >
        <AppAvatar :initials="initials(row.name)" />

        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium text-ink">{{ row.name }}</p>
          <p class="text-xs text-ink-subtle">
            <span class="text-ink">{{ row.succeeded }} hit</span>
            ·
            {{ row.failed }} missed
            <template v-if="row.isCurrentWeekOpen">
              · this week open ({{ row.completedThisWeek }}/{{ targetCount }})
            </template>
          </p>
        </div>

        <!-- Full width below the name on phones: a fixed-width bar beside the text squeezes
             the name into an ellipsis at 375px. -->
        <div class="flex w-full items-center gap-3 sm:w-40 sm:shrink-0">
          <ProgressBar :percent="row.percent" :complete="row.percent === 100" class="flex-1" />
          <span class="w-9 text-right text-xs tabular-nums text-ink-muted">{{ row.percent }}%</span>
        </div>
      </li>
    </ul>
  </AppCard>
</template>
