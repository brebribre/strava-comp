import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useUiStore } from '@/stores/useUiStore'

/**
 * The mobile navigation drawer.
 *
 * Containers reach the store through here, per the layering rule. Navigating always
 * closes the drawer — otherwise tapping a group leaves it covering the page you just
 * asked for.
 */
export function useSidebar() {
  const store = useUiStore()
  const route = useRoute()

  watch(() => route.fullPath, store.close)

  return {
    isOpen: computed(() => store.sidebarOpen),
    open: store.open,
    close: store.close,
    toggle: store.toggle,
  }
}
