import { computed, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import { useAuth } from '@/hooks/useAuth'
import type { TargetWeek } from '@/types/api'

export interface WeekRow {
  key: string
  label: string
  isCurrent: boolean
  targetCount: number
  mine: { completed: number; percent: number; isComplete: boolean } | null
  others: { athlete_id: number; name: string; completed: number; is_complete: boolean }[]
}

/** Week-by-week progress against the group's target, newest first. */
export function useTargetHistory(groupId: () => number, weeks = 12) {
  const api = useGroupApi()
  const { athlete } = useAuth()

  const history = ref<TargetWeek[]>([])
  const targetCount = ref(0)
  const hasTarget = ref(true)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      const data = await api.targetHistory(id, weeks)
      history.value = data.weeks
      targetCount.value = data.target_count
      hasTarget.value = true
    } catch (err) {
      // 404 just means no target set — the widget hides rather than erroring.
      if (err instanceof ApiError && err.status === 404) {
        hasTarget.value = false
        history.value = []
      } else {
        error.value = err instanceof ApiError ? err.message : 'Could not load weekly progress'
      }
    } finally {
      isLoading.value = false
    }
  }

  function weekLabel(week: TargetWeek): string {
    const start = new Date(week.week_start)
    const end = new Date(week.week_end)
    end.setDate(end.getDate() - 1)
    const fmt = (d: Date) =>
      d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', timeZone: 'UTC' })
    return `${fmt(start)} – ${fmt(end)}`
  }

  const rows = computed<WeekRow[]>(() =>
    history.value.map((week) => {
      const mine = week.members.find((m) => m.athlete_id === athlete.value?.athlete_id)
      return {
        key: week.week_start,
        label: week.is_current ? 'This week' : weekLabel(week),
        isCurrent: week.is_current,
        targetCount: week.target_count,
        mine: mine
          ? { completed: mine.completed, percent: mine.percent, isComplete: mine.is_complete }
          : null,
        others: week.members
          .filter((m) => m.athlete_id !== athlete.value?.athlete_id)
          .map((m) => ({
            athlete_id: m.athlete_id,
            name: m.name,
            completed: m.completed,
            is_complete: m.is_complete,
          })),
      }
    }),
  )

  /** How many of the shown weeks the athlete actually hit — the headline for the widget. */
  const weeksHit = computed(() => rows.value.filter((r) => r.mine?.isComplete).length)

  watch(groupId, refresh, { immediate: true })

  return { rows, targetCount, weeksHit, hasTarget, isLoading, error, refresh }
}
