<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useGroupTarget } from '@/hooks/useGroupTarget'
import AppAlert from '@/reusables/AppAlert.vue'
import AppAvatar from '@/reusables/AppAvatar.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import IconDone from '~icons/material-symbols/check-circle-rounded'

/**
 * Everyone else's standing against the target, for the current period only.
 *
 * Reads the same progress endpoint the hero above it does, rather than the weekly history:
 * the question here is "where is everyone this week", which is exactly what progress
 * answers, and it keeps the two panels from disagreeing.
 */
const route = useRoute()
const { athlete } = useAuth()

const { progress, others, hasTarget, periodLabel, isLoading, error } = useGroupTarget(
  () => Number(route.params.id),
  () => athlete.value?.athlete_id,
)
const { initials } = useFormat()
</script>

<template>
  <AppCard v-if="hasTarget" title="Others">
    <template #actions>
      <span class="text-xs text-ink-subtle">{{ periodLabel }}</span>
    </template>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" :size="36" class="py-6" />

    <p v-else-if="!others.length" class="py-2 text-sm text-ink-subtle">
      No one else in this group yet.
    </p>

    <ul v-else class="divide-y divide-line">
      <li
        v-for="member in others"
        :key="member.athlete_id"
        class="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
      >
        <AppAvatar :initials="initials(member.name)" :color-seed="member.athlete_id" />
        <p class="min-w-0 flex-1 truncate text-sm font-medium text-ink">{{ member.name }}</p>

        <!-- Done is a mark, not a number: the only thing worth reading across a list of
             people is who is there and who isn't. -->
        <IconDone
          v-if="member.is_complete"
          class="size-6 shrink-0 text-accent"
          :aria-label="`${member.name} has hit the target`"
        />
        <span v-else class="shrink-0 text-sm tabular-nums text-ink-muted">
          {{ member.completed }}<span class="text-ink-subtle">/{{ progress?.target.count }}</span>
        </span>
      </li>
    </ul>
  </AppCard>
</template>
