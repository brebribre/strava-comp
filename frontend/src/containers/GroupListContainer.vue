<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useGroups } from '@/hooks/useGroups'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppModal from '@/reusables/AppModal.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import AppInput from '@/reusables/AppInput.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import IconAdd from '~icons/material-symbols/add-rounded'
import IconChevronRight from '~icons/material-symbols/chevron-right-rounded'
import IconGroups from '~icons/material-symbols/groups-rounded'

const router = useRouter()
const { groups, isLoading, error, refresh, create, join } = useGroups()

const newName = ref('')
const inviteCode = ref('')
const isSubmitting = ref(false)
const isAddOpen = ref(false)

onMounted(refresh)

function openGroup(id: number) {
  router.push({ name: 'group', params: { id } })
}

async function handleCreate() {
  isSubmitting.value = true
  const group = await create(newName.value.trim())
  isSubmitting.value = false
  if (group) {
    newName.value = ''
    isAddOpen.value = false
    openGroup(group.id)
  }
}

async function handleJoin() {
  isSubmitting.value = true
  const group = await join(inviteCode.value.trim())
  isSubmitting.value = false
  if (group) {
    inviteCode.value = ''
    isAddOpen.value = false
    openGroup(group.id)
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <header class="flex items-center justify-between gap-3">
      <PageTitle>Groups</PageTitle>
      <button
        type="button"
        aria-label="Add a group"
        class="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent text-accent-contrast transition-transform duration-(--duration-quick) ease-(--ease-out-soft) hover:-translate-y-px"
        @click="isAddOpen = true"
      >
        <IconAdd class="size-6" aria-hidden="true" />
      </button>
    </header>

    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>

    <SportLoader v-if="isLoading" label="Loading your groups…" class="py-12" />

    <EmptyState
      v-else-if="!groups.length"
      title="You're not in any groups yet"
      hint="Use + to create one and share the invite link, or join with a code someone sent you."
    />

    <!-- One row per group, the same shape as the recap: the name carries the row and the
         chevron says it opens. -->
    <div v-else class="space-y-3">
      <AppCard
        v-for="group in groups"
        :key="group.id"
        interactive
        class="animate-rise"
        @click="openGroup(group.id)"
      >
        <div class="flex items-center gap-3 sm:gap-5">
          <IconGroups class="size-9 shrink-0 text-accent sm:size-14" aria-hidden="true" />

          <div class="min-w-0 flex-1">
            <h2 class="truncate text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              {{ group.name }}
            </h2>
            <p class="mt-1 text-xs text-ink-muted sm:text-sm">
              {{ group.member_count }} member{{ group.member_count === 1 ? '' : 's' }}
            </p>
          </div>

          <IconChevronRight class="size-6 shrink-0 text-ink-subtle" aria-hidden="true" />
        </div>
      </AppCard>
    </div>

    <AppModal v-if="isAddOpen" title="Add a group" @close="isAddOpen = false">
      <form class="space-y-3" @submit.prevent="handleCreate">
        <AppInput v-model="newName" label="Group name" placeholder="Alvin Brothers" />
        <AppButton type="submit" class="w-full" :loading="isSubmitting" :disabled="!newName.trim()">
          Create group
        </AppButton>
      </form>

      <div class="my-5 flex items-center gap-3 text-[11px] uppercase tracking-wider text-ink-subtle">
        <span class="h-px flex-1 bg-line" />
        or join one
        <span class="h-px flex-1 bg-line" />
      </div>

      <form class="space-y-3" @submit.prevent="handleJoin">
        <AppInput v-model="inviteCode" label="Invite code" placeholder="53uIjRQh" />
        <AppButton
          type="submit"
          variant="secondary"
          class="w-full"
          :loading="isSubmitting"
          :disabled="!inviteCode.trim()"
        >
          Join group
        </AppButton>
      </form>
    </AppModal>
  </div>
</template>
