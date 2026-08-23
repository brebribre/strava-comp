<script setup lang="ts">
withDefaults(defineProps<{ label?: string; size?: number }>(), { size: 44 })
</script>

<template>
  <!--
    The cycle is pure CSS: every icon runs the same keyframes with a staggered delay, so
    there is no timer to own and nothing for a container to drive. That keeps this a
    presentational reusable, and `prefers-reduced-motion` (handled globally) stops it dead.
  -->
  <div class="flex flex-col items-center gap-3 py-10" role="status" :aria-label="label ?? 'Loading'">
    <div class="sport-cycle relative" :style="{ width: `${size}px`, height: `${size}px` }">
      <!-- Run -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <circle cx="29" cy="10" r="4" stroke="currentColor" stroke-width="2.5" />
        <path
          d="M31 17 L22 22 L25 29 L20 38 M25 29 L33 32 L35 40 M22 22 L13 25 M31 17 L38 21"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>

      <!-- Ride -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <circle cx="11" cy="33" r="8" stroke="currentColor" stroke-width="2.5" />
        <circle cx="37" cy="33" r="8" stroke="currentColor" stroke-width="2.5" />
        <circle cx="30" cy="9" r="3.5" stroke="currentColor" stroke-width="2.5" />
        <path
          d="M11 33 L20 33 L27 20 L33 20 M20 33 L28 16 M37 33 L31 20"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>

      <!-- Swim -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <circle cx="17" cy="15" r="4" stroke="currentColor" stroke-width="2.5" />
        <path
          d="M8 26 L22 21 L34 25 L41 15"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <path
          d="M5 36c4 0 4-3 8-3s4 3 8 3 4-3 8-3 4 3 8 3 4-3 8-3"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        />
      </svg>

      <!-- Tennis -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <ellipse
          cx="20"
          cy="18"
          rx="11"
          ry="13"
          transform="rotate(-30 20 18)"
          stroke="currentColor"
          stroke-width="2.5"
        />
        <path
          d="M27 28 L38 40"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        />
        <circle cx="38" cy="17" r="4" stroke="currentColor" stroke-width="2.5" />
      </svg>

      <!-- Weights -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <path
          d="M16 24 H32"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        />
        <rect x="8" y="16" width="7" height="16" rx="2" stroke="currentColor" stroke-width="2.5" />
        <rect x="33" y="16" width="7" height="16" rx="2" stroke="currentColor" stroke-width="2.5" />
        <path d="M4 20 V28 M44 20 V28" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
      </svg>
    </div>

    <p v-if="label" class="text-sm text-ink-muted">{{ label }}</p>
  </div>
</template>

<style scoped>
.sport-cycle {
  color: var(--color-ink-muted);
}

.sport-icon {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  /* 5 icons × 1.1s each. Each one fades in, holds, bobs, then fades out. */
  animation: sport-swap 5.5s var(--ease-out-soft) infinite;
}

.sport-icon:nth-child(1) { animation-delay: 0s; }
.sport-icon:nth-child(2) { animation-delay: 1.1s; }
.sport-icon:nth-child(3) { animation-delay: 2.2s; }
.sport-icon:nth-child(4) { animation-delay: 3.3s; }
.sport-icon:nth-child(5) { animation-delay: 4.4s; }

@keyframes sport-swap {
  0% {
    opacity: 0;
    transform: translateY(5px) scale(0.94);
  }
  4% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  /* A small bob mid-hold, so the icon reads as moving rather than parked. */
  10% {
    transform: translateY(-3px) scale(1);
  }
  16% {
    transform: translateY(0) scale(1);
  }
  20% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  24% {
    opacity: 0;
    transform: translateY(-5px) scale(0.94);
  }
  100% {
    opacity: 0;
  }
}

/* The global reduced-motion rule collapses the duration; hold the first icon steady. */
@media (prefers-reduced-motion: reduce) {
  .sport-icon {
    animation: none;
  }
  .sport-icon:nth-child(1) {
    opacity: 1;
  }
}
</style>
