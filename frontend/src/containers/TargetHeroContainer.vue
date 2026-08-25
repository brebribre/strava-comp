<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useGroupTarget } from '@/hooks/useGroupTarget'
import { useViewport } from '@/hooks/useViewport'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import ProgressRing from '@/reusables/ProgressRing.vue'

/**
 * The "where I stand" block, shared by the Target tab and the top of the Feed.
 *
 * `showEdit` is off by default: on the feed this is a status glance, not a settings entry.
 * `hideWhenUnset` lets the feed stay quiet when no target exists, while the Target tab
 * shows its own empty state instead.
 */
withDefaults(defineProps<{ showEdit?: boolean; hideWhenUnset?: boolean }>(), {
  showEdit: false,
  hideWhenUnset: false,
})

const route = useRoute()
const router = useRouter()
const { athlete } = useAuth()

const { progress, me, hasTarget, headline, periodLabel, isLoading } = useGroupTarget(
  () => Number(route.params.id),
  () => athlete.value?.athlete_id,
)
const { utcDate } = useFormat()
const { isMobile } = useViewport()
const ringSize = computed(() => (isMobile.value ? 150 : 190))

function openSettings() {
  router.push({ name: 'group-settings-target', params: { id: route.params.id } })
}
</script>

<template>
  <AppCard v-if="!isLoading && hasTarget && progress && me" class="animate-rise">
    <div class="flex flex-col items-center gap-6 py-2 sm:flex-row sm:justify-center sm:gap-10">
      <ProgressRing :percent="me.percent" :complete="me.is_complete" :size="ringSize">
        <span class="text-3xl font-bold tabular-nums text-ink">
          {{ me.completed }}<span class="text-ink-subtle">/{{ progress.target.count }}</span>
        </span>
        <span class="mt-0.5 text-[11px] uppercase tracking-wider text-ink-subtle">
          {{ periodLabel }}
        </span>
      </ProgressRing>

      <div class="text-center sm:text-left">
        <p class="text-xl font-bold tracking-tight text-ink">{{ headline }}</p>
        <p class="mt-2 text-sm text-ink-muted">
          {{ progress.target.count }} exercises per {{ progress.target.period }} · until
          {{ utcDate(progress.target.until) }}
        </p>
        <p class="mt-1 text-sm text-ink-muted">
          {{ progress.days_left_in_period }} day{{ progress.days_left_in_period === 1 ? '' : 's' }}
          left in this {{ progress.target.period }} ·
          {{ progress.periods_remaining }} {{ progress.target.period
          }}{{ progress.periods_remaining === 1 ? '' : 's' }} remaining
        </p>
        <AppButton v-if="showEdit" variant="ghost" class="mt-3 -ml-3.5" @click="openSettings">
          Edit target
        </AppButton>
      </div>
    </div>
  </AppCard>
</template>
