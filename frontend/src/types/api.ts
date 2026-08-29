/** Response shapes mirroring the FastAPI backend. Keep in sync with backend/app/schemas/. */

export interface Athlete {
  athlete_id: number
  name: string
  created_at: string
}

export interface Group {
  id: number
  name: string
  invite_code: string
  created_by: number | null
  created_at: string
  member_count: number
}

export interface GroupMember {
  athlete_id: number
  name: string
  joined_at: string
}

export interface SportSummary {
  sport_type: string
  activity_count: number
  total_distance: number
  total_moving_time: number
  total_elevation_gain: number
  avg_heartrate: number | null
}

export interface MemberSummary {
  athlete_id: number
  name: string
  activity_count: number
  total_distance: number
  total_moving_time: number
  total_elevation_gain: number
  avg_heartrate: number | null
  by_sport: SportSummary[]
}

export interface GroupSummary {
  group_id: number
  group_name: string
  since: string
  until: string
  members: MemberSummary[]
}

export interface SportBucket {
  sport_type: string
  activity_count: number
  total_distance: number
  total_moving_time: number
}

export interface TrendPoint {
  week_start: string
  activity_count: number
  total_distance: number
  total_moving_time: number
  by_sport: SportBucket[]
}

export interface MemberTrend {
  athlete_id: number
  name: string
  weeks: TrendPoint[]
}

export interface GroupTrend {
  group_id: number
  group_name: string
  since: string
  until: string
  members: MemberTrend[]
}

export interface SyncResult {
  athlete_id: number
  since: string
  activities_saved: number
}

export interface Exercise {
  name: string
  /** Free text from the logging app: "20 kg x 12", "10 reps", "1km - 7min". */
  sets: string[]
}

export interface FeedItem {
  activity_id: number
  athlete_id: number
  athlete_name: string
  name: string | null
  sport_type: string | null
  distance: number
  moving_time: number
  elapsed_time: number
  total_elevation_gain: number
  average_heartrate: number | null
  start_date: string
  polyline: string | null
  photo_url: string | null
  exercises: Exercise[]
}

export interface GroupFeed {
  group_id: number
  group_name: string
  items: FeedItem[]
  next_before: string | null
}

export interface Split {
  split: number
  distance: number
  moving_time: number
  elevation_difference: number | null
  average_heartrate: number | null
}

export interface ActivityDetail {
  activity_id: number
  athlete_id: number
  athlete_name: string
  name: string | null
  description: string | null
  sport_type: string | null
  start_date: string
  distance: number
  moving_time: number
  elapsed_time: number
  total_elevation_gain: number
  average_heartrate: number | null
  max_heartrate: number | null
  calories: number | null
  device_name: string | null
  polyline: string | null
  photo_url: string | null
  splits: Split[]
  exercises: Exercise[]
  is_detailed: boolean
}

export type TargetPeriod = 'week' | 'month' | 'year'

export interface SportRule {
  min_minutes: number | null
  min_distance_km: number | null
}

export interface TargetRules {
  default_min_minutes: number
  sports: Record<string, SportRule>
}

export interface TargetWrite {
  count: number
  period: TargetPeriod
  /** When the target begins. Omitted means the start of the current period. */
  starts_at?: string
  until: string
  rules: TargetRules
}

export interface Target extends TargetWrite {
  group_id: number
  starts_at: string
  created_at: string
  updated_at: string
}

export interface MemberProgress {
  athlete_id: number
  name: string
  completed: number
  remaining: number
  is_complete: boolean
  percent: number
}

export interface TargetProgress {
  group_id: number
  group_name: string
  target: Target
  period_start: string
  period_end: string
  days_left_in_period: number
  periods_remaining: number
  is_expired: boolean
  is_pending: boolean
  members: MemberProgress[]
}

export interface TelegramSettings {
  is_configured: boolean
  chat_title: string | null
  pairing_code: string | null
  bot_username: string | null
}

export interface TelegramTestResult {
  sent: boolean
  detail: string
}

export interface SportTotals {
  activity_count: number
  distance: number
  moving_time: number
  elevation: number
  avg_heartrate: number | null
}

export interface SportOverview {
  sport_type: string
  current: SportTotals
  previous: SportTotals
  growth_activity_count: number | null
  growth_distance: number | null
  growth_moving_time: number | null
  first_seen: string
  last_seen: string
}

export interface RecapOverview {
  since: string
  until: string
  days: number
  total: SportTotals
  previous_total: SportTotals
  sports: SportOverview[]
  baseline_complete: boolean
  first_activity: string | null
}

export interface MonthPoint {
  month: string
  activity_count: number
  distance: number
  moving_time: number
  elevation: number
  avg_heartrate: number | null
  avg_pace_seconds_per_km: number | null
  avg_speed_kmh: number | null
}

export interface BestEffort {
  label: string
  value: string
  activity_id: number
  activity_name: string | null
  start_date: string
}

export interface Consistency {
  active_weeks: number
  total_weeks: number
  longest_streak_weeks: number
  avg_per_week: number
  longest_gap_days: number
}

export interface SportRecap {
  sport_type: string
  since: string
  until: string
  totals: SportTotals
  months: MonthPoint[]
  bests: BestEffort[]
  consistency: Consistency
}

export interface ZoneBucket {
  zone: number
  label: string
  low_pct: number
  high_pct: number
  low_bpm: number
  high_bpm: number
  activity_count: number
  distance: number
  moving_time: number
  avg_heartrate: number | null
  avg_pace_seconds_per_km: number | null
  previous_activity_count: number
  previous_avg_pace_seconds_per_km: number | null
  pace_delta_seconds: number | null
}

export interface ZoneMonthPoint {
  month: string
  zone: number
  activity_count: number
  avg_pace_seconds_per_km: number | null
}

export interface ZoneRecap {
  sport_type: string
  since: string
  until: string
  hr_max: number
  hr_max_basis: string
  zones: ZoneBucket[]
  months: ZoneMonthPoint[]
  classified_count: number
  unclassified_count: number
}

export interface WeekMemberProgress {
  athlete_id: number
  name: string
  completed: number
  remaining: number
  is_complete: boolean
  percent: number
}

export interface TargetWeek {
  week_start: string
  week_end: string
  is_current: boolean
  /** False for weeks outside the target's window — not a failure, just not covered. */
  in_scope: boolean
  target_count: number
  members: WeekMemberProgress[]
}

export interface TargetHistory {
  group_id: number
  group_name: string
  target_count: number
  period: TargetPeriod
  weeks: TargetWeek[]
}
