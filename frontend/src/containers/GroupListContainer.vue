<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useGroups } from '@/hooks/useGroups'
import { useInviteLink } from '@/hooks/useInviteLink'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import SportLoader from '@/reusables/SportLoader.vue'
import AppInput from '@/reusables/AppInput.vue'
import EmptyState from '@/reusables/EmptyState.vue'

const router = useRouter()
const { groups, isLoading, error, refresh, create, join } = useGroups()

const copyTargetCode = ref<string | undefined>(undefined)
const { copy: copyLink, copied } = useInviteLink(() => copyTargetCode.value)

async function copyInvite(code: string) {
  copyTargetCode.value = code
  await copyLink()
}

const newName = ref('')
const inviteCode = ref('')
const isSubmitting = ref(false)

onMounted(refresh)

async function handleCreate() {
  isSubmitting.value = true
  const group = await create(newName.value.trim())
  isSubmitting.value = false
  if (group) {
    newName.value = ''
    router.push({ name: 'group', params: { id: group.id } })
  }
}

async function handleJoin() {
  isSubmitting.value = true
  const group = await join(inviteCode.value.trim())
  isSubmitting.value = false
  if (group) {
    inviteCode.value = ''
    router.push({ name: 'group', params: { id: group.id } })
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <AppAlert v-if="error" tone="error">{{ error }}</AppAlert>

    <div class="grid gap-6 sm:grid-cols-2">
      <AppCard title="Create a group">
        <form class="space-y-3" @submit.prevent="handleCreate">
          <AppInput v-model="newName" label="Group name" placeholder="Alvin Brothers" />
          <AppButton type="submit" :loading="isSubmitting" :disabled="!newName.trim()">
            Create
          </AppButton>
        </form>
      </AppCard>

      <AppCard title="Join a group">
        <form class="space-y-3" @submit.prevent="handleJoin">
          <AppInput v-model="inviteCode" label="Invite code" placeholder="53uIjRQh" />
          <AppButton
            type="submit"
            variant="secondary"
            :loading="isSubmitting"
            :disabled="!inviteCode.trim()"
          >
            Join
          </AppButton>
        </form>
      </AppCard>
    </div>

    <AppCard title="Your groups">
      <SportLoader v-if="isLoading" :size="36" class="py-6" />
      <EmptyState
        v-else-if="!groups.length"
        title="You're not in any groups yet"
        hint="Create one and share the invite code, or join with a code someone sent you."
      />
      <ul v-else class="divide-y divide-line">
        <li
          v-for="group in groups"
          :key="group.id"
          class="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div>
            <p class="font-medium text-ink">{{ group.name }}</p>
            <p class="text-xs text-ink-muted">
              {{ group.member_count }} member{{ group.member_count === 1 ? '' : 's' }} · invite
              <code class="rounded-sm bg-raised px-1 py-0.5">{{
                group.invite_code
              }}</code>
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <AppButton variant="ghost" @click="copyInvite(group.invite_code)">
              {{ copied && copyTargetCode === group.invite_code ? 'Link copied' : 'Copy link' }}
            </AppButton>
            <AppButton
              variant="ghost"
              @click="router.push({ name: 'group-settings', params: { id: group.id } })"
            >
              Target
            </AppButton>
            <AppButton
              variant="secondary"
              @click="router.push({ name: 'group', params: { id: group.id } })"
            >
              Open
            </AppButton>
          </div>
        </li>
      </ul>
    </AppCard>
  </div>
</template>
