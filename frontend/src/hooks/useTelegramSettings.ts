import { ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'

/** Connecting a group to a Telegram chat, and proving the connection works. */
export function useTelegramSettings(groupId: () => number) {
  const api = useGroupApi()

  const chatId = ref('')
  const isConfigured = ref(false)
  const botUsername = ref<string | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const isTesting = ref(false)
  const error = ref<string | null>(null)
  const notice = ref<string | null>(null)

  async function load() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      const settings = await api.telegram(id)
      chatId.value = settings.telegram_chat_id?.toString() ?? ''
      isConfigured.value = settings.is_configured
      botUsername.value = settings.bot_username
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load Telegram settings'
    } finally {
      isLoading.value = false
    }
  }

  async function save() {
    isSaving.value = true
    error.value = null
    notice.value = null
    try {
      // An empty field means "disconnect", which the API expresses as null.
      const trimmed = chatId.value.trim()
      const parsed = trimmed === '' ? null : Number(trimmed)
      if (parsed !== null && !Number.isInteger(parsed)) {
        error.value = 'Chat id must be a whole number, e.g. -1001234567890'
        return false
      }
      const settings = await api.saveTelegram(groupId(), parsed)
      isConfigured.value = settings.is_configured
      notice.value = settings.is_configured ? 'Telegram connected' : 'Telegram disconnected'
      return true
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not save'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function sendTest() {
    isTesting.value = true
    error.value = null
    notice.value = null
    try {
      const result = await api.testTelegram(groupId())
      notice.value = result.detail
      return true
    } catch (err) {
      // Telegram's own wording ("chat not found", "bot was kicked") is the useful part.
      error.value = err instanceof ApiError ? err.message : 'Test failed'
      return false
    } finally {
      isTesting.value = false
    }
  }

  watch(groupId, load, { immediate: true })

  return {
    chatId, isConfigured, botUsername,
    isLoading, isSaving, isTesting,
    error, notice,
    load, save, sendTest,
  }
}
