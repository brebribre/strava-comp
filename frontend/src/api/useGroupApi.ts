import { request } from '@/api/request'
import type {
  Group,
  GroupFeed,
  GroupMember,
  GroupSummary,
  GroupTrend,
  Target,
  TargetProgress,
  TargetWrite,
  TelegramSettings,
  TelegramTestResult,
} from '@/types/api'

export function useGroupApi() {
  return {
    list: () => request<Group[]>('GET', '/groups'),
    create: (name: string) => request<Group>('POST', '/groups', { name }),
    join: (inviteCode: string) => request<Group>('POST', '/groups/join', { invite_code: inviteCode }),
    members: (groupId: number) => request<GroupMember[]>('GET', `/groups/${groupId}/members`),
    summary: (groupId: number, days: number) =>
      request<GroupSummary>('GET', `/groups/${groupId}/summary?days=${days}`),
    trend: (groupId: number, days: number) =>
      request<GroupTrend>('GET', `/groups/${groupId}/trend?days=${days}`),
    target: (groupId: number) => request<Target>('GET', `/groups/${groupId}/target`),
    saveTarget: (groupId: number, target: TargetWrite) =>
      request<Target>('PUT', `/groups/${groupId}/target`, target),
    deleteTarget: (groupId: number) => request<void>('DELETE', `/groups/${groupId}/target`),
    targetProgress: (groupId: number) =>
      request<TargetProgress>('GET', `/groups/${groupId}/target/progress`),
    telegram: (groupId: number) => request<TelegramSettings>('GET', `/groups/${groupId}/telegram`),
    saveTelegram: (groupId: number, chatId: number | null) =>
      request<TelegramSettings>('PUT', `/groups/${groupId}/telegram`, { telegram_chat_id: chatId }),
    testTelegram: (groupId: number) =>
      request<TelegramTestResult>('POST', `/groups/${groupId}/telegram/test`),
    feed: (groupId: number, limit: number, before?: string | null) =>
      request<GroupFeed>(
        'GET',
        `/groups/${groupId}/feed?limit=${limit}${before ? `&before=${encodeURIComponent(before)}` : ''}`,
      ),
  }
}
