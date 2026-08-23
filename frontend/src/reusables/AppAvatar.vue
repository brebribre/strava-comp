<script setup lang="ts">
defineProps<{ initials: string; colorSeed?: number }>()
</script>

<template>
  <!-- Monochrome: identity is carried by initials, not by a colour per person. -->
  <span
    class="inline-flex size-9 shrink-0 items-center justify-center rounded-md border border-line bg-raised text-[11px] font-semibold tracking-wide text-ink-muted"
  >
    {{ initials }}
  </span>
</template>
