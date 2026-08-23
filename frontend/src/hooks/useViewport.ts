import { onMounted, onUnmounted, ref } from 'vue'

// Matches Tailwind's `sm` breakpoint, so CSS and JS agree on what "mobile" means.
const MOBILE_MAX_WIDTH = 640

/** Reactive viewport size, for the few cases CSS can't express — e.g. an SVG's pixel size. */
export function useViewport() {
  const isMobile = ref(
    typeof window !== 'undefined' ? window.innerWidth < MOBILE_MAX_WIDTH : false,
  )

  function update() {
    isMobile.value = window.innerWidth < MOBILE_MAX_WIDTH
  }

  onMounted(() => window.addEventListener('resize', update))
  onUnmounted(() => window.removeEventListener('resize', update))

  return { isMobile }
}
