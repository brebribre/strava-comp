<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useFormat } from '@/hooks/useFormat'
import { useGroup } from '@/hooks/useGroup'
import { useGroupMembers } from '@/hooks/useGroupMembers'
import { useInviteLink } from '@/hooks/useInviteLink'
import AppAlert from '@/reusables/AppAlert.vue'
import AppAvatar from '@/reusables/AppAvatar.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import EmptyState from '@/reusables/EmptyState.vue'

const route = useRoute()
const groupId = () => Number(route.params.id)

const { rows, isLoading, error } = useGroupMembers(groupId)
const { group } = useGroup(groupId)
const { url, copy, copied } = useInviteLink(() => group.value?.invite_code)
const { initials, utcDate } = useFormat()
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>
    <SportLoader v-else-if="isLoading" label="Loading members…" />

    <template v-else>
      <AppCard :title="`${rows.length} member${rows.length === 1 ? '' : 's'}`">
        <EmptyState v-if="!rows.length" title="No members yet" />
        <ul v-else class="divide-y divide-line">
          <li
            v-for="row in rows"
            :key="row.athlete_id"
            class="animate-rise flex items-center gap-3 py-3 first:pt-0 last:pb-0"
          >
            <AppAvatar :initials="initials(row.name)" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-ink">
                {{ row.name }}
                <span
                  v-if="row.isYou"
                  class="ml-1.5 rounded-sm border border-line px-1.5 py-0.5 text-[11px] font-normal text-ink-muted"
                >
                  You
                </span>
              </p>
              <p class="text-xs text-ink-subtle">Joined {{ utcDate(row.joined_at) }}</p>
            </div>
          </li>
        </ul>
      </AppCard>

      <AppCard title="Invite someone">
        <p class="mb-3 text-sm text-ink-muted">
          Anyone opening this link joins the group — they'll be asked to connect Strava if they
          haven't already.
        </p>
        <div class="flex flex-wrap items-center gap-2">
          <code
            class="min-w-0 flex-1 truncate rounded-sm border border-line bg-raised px-2 py-1.5 text-xs text-ink-muted"
          >
            {{ url }}
          </code>
          <AppButton variant="secondary" @click="copy">
            {{ copied ? 'Copied' : 'Copy link' }}
          </AppButton>
        </div>
      </AppCard>
    </template>
  </div>
</template>
