<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost'
    type?: 'button' | 'submit'
    disabled?: boolean
    loading?: boolean
  }>(),
  { variant: 'primary', type: 'button', disabled: false, loading: false },
)

defineEmits<{ click: [MouseEvent] }>()

// Monochrome: emphasis comes from fill vs outline vs bare, not from hue.
const styles = {
  primary: 'bg-accent text-accent-contrast hover:opacity-90',
  secondary: 'bg-surface text-ink ring-1 ring-line-strong hover:bg-raised',
  ghost: 'text-ink-muted hover:bg-raised hover:text-ink',
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium',
      'transition-all duration-(--duration-quick) ease-(--ease-out-soft)',
      // The press is the animation: a barely-there scale that makes the click feel physical.
      'active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100',
      'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
      styles[variant],
    ]"
    @click="$emit('click', $event)"
  >
    <span
      v-if="loading"
      class="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
    <slot />
  </button>
</template>
