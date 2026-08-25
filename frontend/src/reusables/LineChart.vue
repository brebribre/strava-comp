<script setup lang="ts">
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, BarElement, CategoryScale, LinearScale, Filler)

defineProps<{ data: any; options?: any; height?: number }>()
</script>

<template>
  <div :style="{ height: `${height ?? 280}px` }">
    <Line :data="data" :options="options" />
  </div>
</template>
