import { defineStore } from 'pinia'
import { ref } from 'vue'

export type TintLevel = 'none' | 'subtle' | 'strong'

/** Appearance settings. Kept on the device — this is a display preference, not account data. */
export const useThemeStore = defineStore('theme', () => {
  // null means monochrome: the accent falls back to ink.
  const accent = ref<string | null>(null)
  // How much of the accent bleeds into page and card backgrounds.
  const tint = ref<TintLevel>('subtle')
  const isLoaded = ref(false)

  function set(nextAccent: string | null, nextTint?: TintLevel) {
    accent.value = nextAccent
    if (nextTint) tint.value = nextTint
    isLoaded.value = true
  }

  return { accent, tint, isLoaded, set }
})
