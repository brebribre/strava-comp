<script setup lang="ts">
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Title,
  Tooltip,
} from 'chart.js'
import { Bar } from 'vue-chartjs'

// Registering only what's used keeps the bundle down — Chart.js is tree-shakeable.
ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

defineProps<{ data: any; options?: any; height?: number }>()
</script>

<template>
  <div :style="{ height: `${height ?? 320}px` }">
    <Bar :data="data" :options="options" />
  </div>
</template>
