<script setup lang="ts">
withDefaults(defineProps<{ label: string; active?: boolean; color?: string }>(), {
  active: false,
})

defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    type="button"
    :class="[
      'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium',
      'transition-all duration-(--duration-quick) ease-(--ease-out-soft) active:scale-[0.97]',
      active
        ? 'border-accent bg-accent text-accent-contrast'
        : 'border-line text-ink-muted hover:border-line-strong hover:text-ink',
    ]"
    @click="$emit('toggle')"
  >
    <!-- The swatch is the one place hue survives: it ties a chip to its chart series. -->
    <span
      v-if="color"
      class="size-1.5 rounded-full"
      :style="{ backgroundColor: color }"
      aria-hidden="true"
    />
    {{ label }}
  </button>
</template>
