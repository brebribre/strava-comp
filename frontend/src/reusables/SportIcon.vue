<script setup lang="ts">
import { computed } from 'vue'

import IconBadminton from '~icons/material-symbols/badminton'
import IconBasketball from '~icons/material-symbols/sports-basketball'
import IconExercise from '~icons/material-symbols/exercise'
import IconFootball from '~icons/material-symbols/sports-soccer'
import IconGolf from '~icons/material-symbols/sports-golf'
import IconHike from '~icons/material-symbols/hiking'
import IconRide from '~icons/material-symbols/directions-bike'
import IconRow from '~icons/material-symbols/rowing'
import IconRun from '~icons/material-symbols/directions-run'
import IconSki from '~icons/material-symbols/downhill-skiing'
import IconSwim from '~icons/material-symbols/pool'
import IconTennis from '~icons/material-symbols/sports-tennis'
import IconWalk from '~icons/material-symbols/directions-walk'
import IconWeights from '~icons/material-symbols/fitness-center'
import IconYoga from '~icons/material-symbols/self-improvement'
import { useSportIcon, type SportFamily } from '@/hooks/useSportIcon'

const props = defineProps<{ sport: string | null; size?: number }>()

const { resolve } = useSportIcon()

// Material Symbols (Apache 2.0), compiled in at build time by unplugin-icons.
const ICONS: Record<SportFamily, unknown> = {
  Run: IconRun,
  Ride: IconRide,
  Swim: IconSwim,
  Tennis: IconTennis,
  Badminton: IconBadminton,
  WeightTraining: IconWeights,
  Walk: IconWalk,
  Hike: IconHike,
  Row: IconRow,
  Ski: IconSki,
  Yoga: IconYoga,
  Football: IconFootball,
  Basketball: IconBasketball,
  Golf: IconGolf,
  Workout: IconExercise,
}

const icon = computed(() => ICONS[resolve(props.sport)])
</script>

<template>
  <component
    :is="icon"
    :style="{ fontSize: `${size ?? 20}px` }"
    class="shrink-0"
    aria-hidden="true"
  />
</template>
