import { computed, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { TargetWeek } from '@/types/api'

export interface MemberRecord {
  athlete_id: number
  name: string
  succeeded: number
  failed: number
  /** True when the current week is still open and not yet hit — neither a win nor a loss. */
  isCurrentWeekOpen: boolean
  completedThisWeek: number
  percent: number
}

/** Week-by-week progress against the group's target, newest first. */
export function useTargetHistory(groupId: () => number, weeks = 12) {
  const api = useGroupApi()

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

  /**
   * One row per member: weeks hit versus weeks missed.
   *
   * The current week is deliberately excluded from both tallies unless it's already been
   * hit — it's still in progress, and counting an unfinished week as a failure would make
   * every Monday look like a loss. Weeks outside the target's own window are skipped
   * entirely: nobody failed a target that hadn't started yet.
   */
  const rows = computed<MemberRecord[]>(() => {
    const weeks = history.value
    if (!weeks.length) return []

    return weeks[0].members.map((member) => {
      let succeeded = 0
      let failed = 0
      let isCurrentWeekOpen = false
      let completedThisWeek = 0

      for (const week of weeks) {
        if (!week.in_scope) continue
        const entry = week.members.find((m) => m.athlete_id === member.athlete_id)
        if (!entry) continue

        if (week.is_current) {
          completedThisWeek = entry.completed
          if (entry.is_complete) succeeded += 1
          else isCurrentWeekOpen = true
          continue
        }

        if (entry.is_complete) succeeded += 1
        else failed += 1
      }

      const decided = succeeded + failed
      return {
        athlete_id: member.athlete_id,
        name: member.name,
        succeeded,
        failed,
        isCurrentWeekOpen,
        completedThisWeek,
        percent: decided ? Math.round((succeeded / decided) * 100) : 0,
      }
    })
  })

  // Best record first — the whole point is comparing.
  const ranked = computed(() =>
    [...rows.value].sort((a, b) => b.succeeded - a.succeeded || a.failed - b.failed),
  )

  const weeksCounted = computed(() => history.value.filter((week) => week.in_scope).length)

  watch(groupId, refresh, { immediate: true })

  return { rows: ranked, targetCount, weeksCounted, hasTarget, isLoading, error, refresh }
}
