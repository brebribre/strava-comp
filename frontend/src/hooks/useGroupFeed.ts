import { ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import { usePolyline } from '@/hooks/usePolyline'
import type { FeedItem, GroupFeed } from '@/types/api'

const PAGE_SIZE = 20

/** A feed item plus its prepared visual, so the container never touches geometry. */
export interface FeedEntry {
  item: FeedItem
  routePath: string | null
}

export interface FeedDay {
  label: string
  entries: FeedEntry[]
}

/**
 * The group's shared timeline, paginated by cursor.
 *
 * Items are grouped into days here rather than in the container, so the template stays a
 * plain v-for over a prepared structure.
 */
export function useGroupFeed(groupId: () => number) {
  const api = useGroupApi()
  const { toSvgPath } = usePolyline()

  const feed = ref<GroupFeed | null>(null)
  const items = ref<FeedItem[]>([])
  const days = ref<FeedDay[]>([])
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const hasMore = ref(false)
  const error = ref<string | null>(null)

  let cursor: string | null = null

  function dayLabel(iso: string): string {
    const date = new Date(iso)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(today.getDate() - 1)

    const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString()
    if (sameDay(date, today)) return 'Today'
    if (sameDay(date, yesterday)) return 'Yesterday'
    return date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
  }

  function regroup() {
    const buckets: FeedDay[] = []
    for (const item of items.value) {
      // Feed thumbnails are wider than tall; the detail page uses its own dimensions.
      const entry: FeedEntry = { item, routePath: toSvgPath(item.polyline, 640, 200, 8) }
      const label = dayLabel(item.start_date)
      const last = buckets.at(-1)
      if (last && last.label === label) last.entries.push(entry)
      else buckets.push({ label, entries: [entry] })
    }
    days.value = buckets
  }

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    cursor = null
    try {
      const result = await api.feed(id, PAGE_SIZE)
      feed.value = result
      items.value = result.items
      cursor = result.next_before
      hasMore.value = result.next_before !== null
      regroup()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load the feed'
      items.value = []
      days.value = []
      hasMore.value = false
    } finally {
      isLoading.value = false
    }
  }

  async function loadMore() {
    const id = groupId()
    if (!cursor || isLoadingMore.value) return
    isLoadingMore.value = true
    try {
      const result = await api.feed(id, PAGE_SIZE, cursor)
      items.value = [...items.value, ...result.items]
      cursor = result.next_before
      hasMore.value = result.next_before !== null
      regroup()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load more'
    } finally {
      isLoadingMore.value = false
    }
  }

  watch(groupId, refresh, { immediate: true })

  return { feed, items, days, isLoading, isLoadingMore, hasMore, error, refresh, loadMore }
}
