<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

defineProps<{ title?: string }>()
const emit = defineEmits<{ close: [] }>()

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true">
    <div class="absolute inset-0 bg-ink-inverse/70" @click="emit('close')" />

    <div
      class="animate-rise relative max-h-[92vh] w-full overflow-y-auto rounded-t-lg bg-surface p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-xl shadow-black/40 sm:max-w-md sm:rounded-lg sm:pb-5"
    >
      <header class="mb-4 flex items-center justify-between gap-4">
        <h2 v-if="title" class="text-sm font-semibold text-ink">{{ title }}</h2>
        <button
          type="button"
          aria-label="Close"
          class="-mr-2 -mt-1 rounded-md p-2 text-ink-muted transition-colors duration-(--duration-quick) hover:bg-raised hover:text-ink"
          @click="emit('close')"
        >
          <svg class="size-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      <slot />
    </div>
  </div>
</template>
