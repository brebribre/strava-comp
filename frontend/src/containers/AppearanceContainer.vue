<script setup lang="ts">
import { ref, watch } from 'vue'

import { useTheme } from '@/hooks/useTheme'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'

const { accent, tint, isMonochrome, presets, tintOptions, set, setTint, isValid } = useTheme()

const custom = ref(accent.value ?? '#0369a1')

// Typing in the hex field previews live, but only once it's a complete colour.
watch(custom, (value) => {
  if (isValid(value)) set(value)
})
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <header>
      <h1 class="text-xl font-bold tracking-tight text-ink">Appearance</h1>
      <p class="mt-1 text-sm text-ink-muted">
        Pick an accent colour. It applies immediately and is remembered on this device.
      </p>
    </header>

    <AppCard title="Accent">
      <div class="grid grid-cols-3 gap-2 sm:grid-cols-4">
        <button
          v-for="preset in presets"
          :key="preset.name"
          type="button"
          :class="[
            'flex items-center gap-2 rounded-md border px-3 py-2 text-left text-xs',
            'transition-all duration-(--duration-quick) active:scale-[0.97]',
            (preset.value ?? null) === accent
              ? 'border-accent bg-accent-soft font-medium text-ink'
              : 'border-line text-ink-muted hover:border-line-strong hover:text-ink',
          ]"
          @click="set(preset.value)"
        >
          <span
            class="size-4 shrink-0 rounded-sm border border-line"
            :style="{
              // Monochrome shows the current ink rather than a colour chip.
              backgroundColor: preset.value ?? 'var(--color-ink)',
            }"
            aria-hidden="true"
          />
          {{ preset.name }}
        </button>
      </div>

      <div class="mt-5 border-t border-line pt-5">
        <p class="mb-1.5 text-xs font-medium text-ink-muted">Background tint</p>
        <p class="mb-3 text-xs text-ink-subtle">
          How much of the colour bleeds into the page and cards.
        </p>
        <div class="flex flex-wrap gap-2">
          <AppButton
            v-for="option in tintOptions"
            :key="option.value"
            :variant="tint === option.value ? 'primary' : 'secondary'"
            :disabled="isMonochrome"
            @click="setTint(option.value)"
          >
            {{ option.label }}
          </AppButton>
        </div>
        <p v-if="isMonochrome" class="mt-2 text-xs text-ink-subtle">
          Pick a colour first — there's nothing to tint with in monochrome.
        </p>
      </div>

      <div class="mt-5 flex flex-wrap items-end gap-3 border-t border-line pt-5">
        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-ink-muted">Custom colour</span>
          <div class="flex items-center gap-2">
            <input
              v-model="custom"
              type="color"
              aria-label="Pick a custom accent colour"
              class="h-9 w-12 cursor-pointer rounded-md border border-line bg-surface p-1"
            />
            <input
              v-model="custom"
              type="text"
              spellcheck="false"
              class="w-28 rounded-md border border-line bg-surface px-3 py-2 font-mono text-sm text-ink outline-none transition-colors duration-(--duration-quick) focus:border-accent"
            />
          </div>
        </label>
        <AppButton v-if="!isMonochrome" variant="ghost" @click="set(null)">
          Reset to monochrome
        </AppButton>
      </div>
    </AppCard>

    <!-- A live sample, so the choice is judged against real components rather than a swatch. -->
    <AppCard title="Preview">
      <div class="space-y-4">
        <div class="flex flex-wrap gap-2">
          <AppButton>Primary</AppButton>
          <AppButton variant="secondary">Secondary</AppButton>
          <AppButton variant="ghost">Ghost</AppButton>
        </div>

        <div>
          <p class="mb-1.5 text-xs text-ink-muted">Progress</p>
          <ProgressBar :percent="68" />
        </div>

        <p class="text-sm text-ink-muted">
          Body text stays monochrome — the accent marks
          <span class="font-medium text-accent">what's active</span>, not everything.
        </p>
      </div>
    </AppCard>
  </div>
</template>
