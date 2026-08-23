<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useGroup } from '@/hooks/useGroup'
import { useInviteLink } from '@/hooks/useInviteLink'
import AppButton from '@/reusables/AppButton.vue'
import TabLink from '@/reusables/TabLink.vue'

const route = useRoute()
const { group } = useGroup(() => Number(route.params.id))
const { copy, copied } = useInviteLink(() => group.value?.invite_code)
</script>

<template>
  <header class="mb-6 border-b border-line">
    <div class="mb-4 flex flex-wrap items-baseline justify-between gap-2">
      <h1 class="min-w-0 truncate text-lg font-bold text-ink sm:text-xl">
        {{ group?.name ?? 'Group' }}
      </h1>
      <div v-if="group" class="flex items-center gap-2 text-xs text-ink-muted">
        <span>{{ group.member_count }} member{{ group.member_count === 1 ? '' : 's' }}</span>
        <AppButton variant="secondary" class="!px-2 !py-1 !text-xs" @click="copy">
          {{ copied ? 'Link copied' : 'Copy invite link' }}
        </AppButton>
      </div>
    </div>

    <nav class="-mb-px flex gap-5 overflow-x-auto whitespace-nowrap sm:gap-6">
      <TabLink :to="{ name: 'group-feed', params: { id: route.params.id } }" label="Feed" />
      <TabLink :to="{ name: 'group-summary', params: { id: route.params.id } }" label="Summary" />
      <TabLink :to="{ name: 'group-target', params: { id: route.params.id } }" label="Target" />
      <TabLink :to="{ name: 'group-members', params: { id: route.params.id } }" label="Members" />
      <TabLink :to="{ name: 'group-settings', params: { id: route.params.id } }" label="Settings" />
    </nav>
  </header>
</template>
