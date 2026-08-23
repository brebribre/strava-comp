import { defineStore } from 'pinia'
import { ref } from 'vue'

/** Ephemeral UI state shared across containers — currently just the mobile drawer. */
export const useUiStore = defineStore('ui', () => {
  const sidebarOpen = ref(false)

  function open() {
    sidebarOpen.value = true
  }
  function close() {
    sidebarOpen.value = false
  }
  function toggle() {
    sidebarOpen.value = !sidebarOpen.value
  }

  return { sidebarOpen, open, close, toggle }
})
