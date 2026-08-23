import { computed, onUnmounted, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'

// While the setup card is open we re-check, so the screen flips to "connected" on its own
// the moment the user sends the command in Telegram.
const POLL_MS = 4000

/**
 * Connecting a group to a Telegram chat.
 *
 * Nobody has to find a chat id: the app shows a pairing code, the user sends
 * "/connect CODE" in their chat, and the bot reports the chat back to us.
 */
export function useTelegramSettings(groupId: () => number) {
  const api = useGroupApi()

  const isConfigured = ref(false)
  const chatTitle = ref<string | null>(null)
  const pairingCode = ref<string | null>(null)
  const botUsername = ref<string | null>(null)

  const isLoading = ref(false)
  const isTesting = ref(false)
  const isDisconnecting = ref(false)
  const error = ref<string | null>(null)
  const notice = ref<string | null>(null)
  const copied = ref(false)

  let timer: ReturnType<typeof setInterval> | null = null

  const connectCommand = computed(() =>
    pairingCode.value ? `/connect ${pairingCode.value}` : '',
  )

  async function load(quiet = false) {
    const id = groupId()
    if (!Number.isFinite(id)) return
    if (!quiet) isLoading.value = true
    try {
      const settings = await api.telegram(id)
      const justConnected = settings.is_configured && !isConfigured.value
      isConfigured.value = settings.is_configured
      chatTitle.value = settings.chat_title
      pairingCode.value = settings.pairing_code
      botUsername.value = settings.bot_username
      if (justConnected) {
        notice.value = `Connected to ${settings.chat_title ?? 'your Telegram chat'}`
        stopPolling()
      }
    } catch (err) {
      if (!quiet) error.value = err instanceof ApiError ? err.message : 'Could not load settings'
    } finally {
      if (!quiet) isLoading.value = false
    }
  }

  function startPolling() {
    if (timer || isConfigured.value) return
    timer = setInterval(() => load(true), POLL_MS)
  }

  function stopPolling() {
    if (timer) clearInterval(timer)
    timer = null
  }

  async function copyCommand() {
    if (!connectCommand.value) return
    try {
      await navigator.clipboard.writeText(connectCommand.value)
    } catch {
      // Clipboard access can be denied; fall back to a selection-based copy.
      const field = document.createElement('textarea')
      field.value = connectCommand.value
      field.style.position = 'fixed'
      field.style.opacity = '0'
      document.body.appendChild(field)
      field.select()
      document.execCommand('copy')
      document.body.removeChild(field)
    }
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  }

  async function sendTest() {
    isTesting.value = true
    error.value = null
    notice.value = null
    try {
      const result = await api.testTelegram(groupId())
      notice.value = result.detail
    } catch (err) {
      // Telegram's own wording ("bot was kicked", "chat not found") is the useful part.
      error.value = err instanceof ApiError ? err.message : 'Test failed'
    } finally {
      isTesting.value = false
    }
  }

  async function disconnect() {
    isDisconnecting.value = true
    error.value = null
    notice.value = null
    try {
      const settings = await api.disconnectTelegram(groupId())
      isConfigured.value = settings.is_configured
      chatTitle.value = settings.chat_title
      pairingCode.value = settings.pairing_code
      notice.value = 'Disconnected'
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not disconnect'
    } finally {
      isDisconnecting.value = false
    }
  }

  watch(groupId, () => load(), { immediate: true })
  onUnmounted(stopPolling)

  return {
    isConfigured, chatTitle, pairingCode, botUsername, connectCommand,
    isLoading, isTesting, isDisconnecting, error, notice, copied,
    load, startPolling, stopPolling, copyCommand, sendTest, disconnect,
  }
}
