import { computed, reactive, ref, watch } from 'vue'

import { useGroupApi } from '@/api/useGroupApi'
import { ApiError } from '@/api/request'
import type { TargetPeriod, TargetWrite } from '@/types/api'

/** Sports offered by default in the editor. Others fall back to the default rule. */
export const KNOWN_SPORTS = ['Run', 'Ride', 'Tennis', 'WeightTraining', 'Swim', 'Walk'] as const

export interface SportRuleForm {
  sport: string
  enabled: boolean
  minMinutes: number | null
  minDistanceKm: number | null
}

function defaultSportRules(): SportRuleForm[] {
  return [
    { sport: 'Run', enabled: true, minMinutes: 20, minDistanceKm: 3 },
    { sport: 'Ride', enabled: false, minMinutes: 30, minDistanceKm: 10 },
    { sport: 'Tennis', enabled: true, minMinutes: 45, minDistanceKm: null },
    { sport: 'WeightTraining', enabled: true, minMinutes: 30, minDistanceKm: null },
    { sport: 'Swim', enabled: false, minMinutes: 20, minDistanceKm: null },
    { sport: 'Walk', enabled: false, minMinutes: 45, minDistanceKm: null },
  ]
}

/** Owns the whole edit form: loading, shaping, validating and saving the target. */
export function useTargetForm(groupId: () => number) {
  const api = useGroupApi()

  const form = reactive({
    count: 4,
    period: 'week' as TargetPeriod,
    startsAt: '',
    until: '',
    defaultMinMinutes: 30,
    sports: defaultSportRules(),
  })

  const exists = ref(false)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const saved = ref(false)

  function defaultUntil(): string {
    const date = new Date()
    date.setFullYear(date.getFullYear() + 1)
    return date.toISOString().slice(0, 10)
  }

  /** Monday of the current week — the target covers the period it is created in. */
  function defaultStartsAt(): string {
    const date = new Date()
    const isoWeekday = (date.getDay() + 6) % 7
    date.setDate(date.getDate() - isoWeekday)
    return date.toISOString().slice(0, 10)
  }

  /** Validation mirrors the backend: the window has to run forwards. */
  const windowError = computed(() =>
    form.startsAt && form.until && form.until <= form.startsAt
      ? 'The end date has to be after the start date'
      : null,
  )

  async function load() {
    const id = groupId()
    if (!Number.isFinite(id)) return
    isLoading.value = true
    error.value = null
    try {
      const target = await api.target(id)
      exists.value = true
      form.count = target.count
      form.period = target.period
      form.startsAt = target.starts_at.slice(0, 10)
      form.until = target.until.slice(0, 10)
      form.defaultMinMinutes = target.rules.default_min_minutes
      form.sports = defaultSportRules().map((row) => {
        const rule = target.rules.sports[row.sport]
        return rule
          ? {
              ...row,
              enabled: true,
              minMinutes: rule.min_minutes,
              minDistanceKm: rule.min_distance_km,
            }
          : { ...row, enabled: false }
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // No target yet — leave the sensible defaults in place.
        exists.value = false
        form.startsAt = defaultStartsAt()
        form.until = defaultUntil()
      } else {
        error.value = err instanceof ApiError ? err.message : 'Could not load the target'
      }
    } finally {
      isLoading.value = false
    }
  }

  function toPayload(): TargetWrite {
    const sports: TargetWrite['rules']['sports'] = {}
    for (const row of form.sports) {
      if (!row.enabled) continue
      sports[row.sport] = {
        min_minutes: row.minMinutes || null,
        min_distance_km: row.minDistanceKm || null,
      }
    }
    return {
      count: form.count,
      period: form.period,
      // Date inputs give bare dates: the target runs from the start of its first day
      // through the end of its last one.
      starts_at: new Date(`${form.startsAt}T00:00:00Z`).toISOString(),
      until: new Date(`${form.until}T23:59:59Z`).toISOString(),
      rules: { default_min_minutes: form.defaultMinMinutes, sports },
    }
  }

  async function save(): Promise<boolean> {
    if (windowError.value) {
      error.value = windowError.value
      return false
    }
    isSaving.value = true
    error.value = null
    saved.value = false
    try {
      await api.saveTarget(groupId(), toPayload())
      exists.value = true
      saved.value = true
      return true
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not save the target'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function remove(): Promise<boolean> {
    isSaving.value = true
    error.value = null
    try {
      await api.deleteTarget(groupId())
      exists.value = false
      form.startsAt = defaultStartsAt()
      form.until = defaultUntil()
      return true
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not remove the target'
      return false
    } finally {
      isSaving.value = false
    }
  }

  watch(groupId, load, { immediate: true })

  return { form, exists, isLoading, isSaving, saved, error, windowError, load, save, remove }
}
