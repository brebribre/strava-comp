<script setup lang="ts">
withDefaults(defineProps<{ label?: string; size?: number }>(), { size: 48 })
</script>

<template>
  <!--
    Two layers of motion, both pure CSS:
      1. which sport is showing — a hard cut every 1.1s, never a fade
      2. the sport itself moving — legs striding, wheels turning, arms stroking
    No timer to own, so this stays a presentational reusable, and the global
    reduced-motion rule stops all of it.
  -->
  <div
    class="flex flex-col items-center gap-3"
    role="status"
    :aria-label="label ?? 'Loading'"
  >
    <div class="sport-cycle relative" :style="{ width: `${size}px`, height: `${size}px` }">
      <!-- ── Run ── -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <g class="run-body">
          <circle cx="30" cy="9" r="4" />
          <path d="M29 14 L24 25" />
        </g>
        <path class="run-arm-a" d="M27 17 L35 21" />
        <path class="run-arm-b" d="M27 17 L18 19" />
        <path class="run-leg-a" d="M24 25 L28 34 L33 37" />
        <path class="run-leg-b" d="M24 25 L17 31 L12 34" />
      </svg>

      <!-- ── Ride ── -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <g class="ride-wheel-a">
          <circle cx="11" cy="34" r="7.5" />
          <path d="M11 26.5 L11 41.5 M3.5 34 L18.5 34" stroke-width="1.6" />
        </g>
        <g class="ride-wheel-b">
          <circle cx="37" cy="34" r="7.5" />
          <path d="M37 26.5 L37 41.5 M29.5 34 L44.5 34" stroke-width="1.6" />
        </g>
        <path d="M11 34 L21 34 L28 21 L33 21 M21 34 L29 18 M37 34 L31 21" />
        <circle cx="31" cy="10" r="3.5" />
        <g class="ride-crank"><path d="M21 34 L25 30" stroke-width="2" /></g>
      </svg>

      <!-- ── Swim ── -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <circle cx="17" cy="15" r="4" />
        <path d="M9 25 L23 21 L35 24" />
        <path class="swim-arm" d="M23 21 L33 13" />
        <path class="swim-wave" d="M-3 36c4 0 4-3 8-3s4 3 8 3 4-3 8-3 4 3 8 3 4-3 8-3 4 3 8 3 4-3 8-3" />
      </svg>

      <!-- ── Tennis ── -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <g class="tennis-racket">
          <ellipse cx="20" cy="18" rx="10" ry="12" transform="rotate(-30 20 18)" />
          <path d="M26 27 L36 39" />
        </g>
        <circle class="tennis-ball" cx="38" cy="16" r="3.5" />
      </svg>

      <!-- ── Weights ── -->
      <svg class="sport-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <g class="weights-bar">
          <path d="M15 24 H33" />
          <rect x="8" y="17" width="6" height="14" rx="1.5" />
          <rect x="34" y="17" width="6" height="14" rx="1.5" />
          <path d="M4 20 V28 M44 20 V28" />
        </g>
      </svg>
    </div>

    <p v-if="label" class="text-sm text-ink-muted">{{ label }}</p>
  </div>
</template>

<style scoped>
.sport-cycle {
  /* Full-contrast ink — white in dark mode, near-black in light. */
  color: var(--color-ink);
}

.sport-icon {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  /* 5 icons × 1.1s. steps(1) makes the swap a hard cut: never a half-faded frame. */
  animation: sport-swap 5.5s steps(1, end) infinite;
}

.sport-icon :is(path, circle, ellipse, rect) {
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

.sport-icon:nth-child(1) { animation-delay: 0s; }
.sport-icon:nth-child(2) { animation-delay: 1.1s; }
.sport-icon:nth-child(3) { animation-delay: 2.2s; }
.sport-icon:nth-child(4) { animation-delay: 3.3s; }
.sport-icon:nth-child(5) { animation-delay: 4.4s; }

@keyframes sport-swap {
  0% { opacity: 1; }
  20% { opacity: 0; }
  100% { opacity: 0; }
}

/* Transforms are expressed in viewBox units, so origins can be written as coordinates. */
.sport-icon g,
.sport-icon path,
.sport-icon circle {
  transform-box: view-box;
}

/* ── Running: legs and arms swing in opposition, body bobs on each stride ── */
.run-body { animation: run-bob 0.52s ease-in-out infinite; transform-origin: 26px 20px; }
.run-leg-a { animation: swing-forward 0.52s ease-in-out infinite; transform-origin: 24px 25px; }
.run-leg-b { animation: swing-back 0.52s ease-in-out infinite; transform-origin: 24px 25px; }
.run-arm-a { animation: swing-back 0.52s ease-in-out infinite; transform-origin: 27px 17px; }
.run-arm-b { animation: swing-forward 0.52s ease-in-out infinite; transform-origin: 27px 17px; }

@keyframes swing-forward {
  0%, 100% { transform: rotate(20deg); }
  50% { transform: rotate(-22deg); }
}
@keyframes swing-back {
  0%, 100% { transform: rotate(-22deg); }
  50% { transform: rotate(20deg); }
}
@keyframes run-bob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-1.5px); }
}

/* ── Cycling: both wheels and the crank turn ── */
.ride-wheel-a { animation: spin 0.7s linear infinite; transform-origin: 11px 34px; }
.ride-wheel-b { animation: spin 0.7s linear infinite; transform-origin: 37px 34px; }
.ride-crank { animation: spin 0.7s linear infinite; transform-origin: 21px 34px; }

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Swimming: the arm strokes over, the water moves past ── */
.swim-arm { animation: stroke 1.1s linear infinite; transform-origin: 23px 21px; }
.swim-wave { animation: drift 1.4s linear infinite; }

@keyframes stroke {
  to { transform: rotate(360deg); }
}
@keyframes drift {
  from { transform: translateX(0); }
  to { transform: translateX(16px); }
}

/* ── Tennis: the racket swings and the ball answers ── */
.tennis-racket { animation: swing 0.75s ease-in-out infinite; transform-origin: 36px 39px; }
.tennis-ball { animation: ball 0.75s ease-in-out infinite; }

@keyframes swing {
  0%, 100% { transform: rotate(-14deg); }
  50% { transform: rotate(12deg); }
}
@keyframes ball {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-5px, 7px); }
}

/* ── Weights: a slow press ── */
.weights-bar { animation: press 1.1s ease-in-out infinite; }

@keyframes press {
  0%, 100% { transform: translateY(4px); }
  50% { transform: translateY(-4px); }
}

@media (prefers-reduced-motion: reduce) {
  .sport-icon,
  .sport-icon * {
    animation: none;
  }
  .sport-icon:nth-child(1) {
    opacity: 1;
  }
}
</style>
