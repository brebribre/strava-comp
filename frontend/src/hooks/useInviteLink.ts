import { computed, ref } from 'vue'

/** Builds and copies the shareable invite URL for a group. */
export function useInviteLink(inviteCode: () => string | undefined) {
  const copied = ref(false)

  const url = computed(() =>
    inviteCode() ? `${window.location.origin}/join/${inviteCode()}` : '',
  )

  async function copy() {
    if (!url.value) return false
    try {
      await navigator.clipboard.writeText(url.value)
    } catch {
      // Clipboard access can be denied (insecure context, permissions). Fall back to a
      // selection-based copy rather than silently doing nothing.
      const field = document.createElement('textarea')
      field.value = url.value
      field.style.position = 'fixed'
      field.style.opacity = '0'
      document.body.appendChild(field)
      field.select()
      document.execCommand('copy')
      document.body.removeChild(field)
    }
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
    return true
  }

  return { url, copy, copied }
}
