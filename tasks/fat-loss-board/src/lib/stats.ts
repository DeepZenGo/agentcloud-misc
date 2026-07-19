import type { DayLog } from './types'
import { isExerciseDay } from './phase'

/** Matches habit-tracker.py: walk newest→oldest, count consecutive full compliance. */
export function computeStreak(records: DayLog[]): number {
  const sorted = [...records].sort((a, b) => b.date.localeCompare(a.date))
  let streak = 0
  for (const r of sorted) {
    if (r.window_8h && r.no_eating_after_8pm) streak += 1
    else break
  }
  return streak
}

export function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const WEEKDAY_SHORT = ['日', '一', '二', '三', '四', '五', '六']

export function weekSummary(records: DayLog[], now: Date = new Date()) {
  const todayKey = formatDate(now)
  const dayOfWeek = (now.getDay() + 6) % 7 // Mon=0 … Sun=6
  const monday = new Date(now)
  monday.setHours(12, 0, 0, 0)
  monday.setDate(now.getDate() - dayOfWeek)

  const byDate = new Map(records.map((r) => [r.date, r]))
  const days = []
  let windowOk = 0
  let noEight = 0
  let exercised = 0
  let logged = 0

  for (let i = 0; i < 7; i++) {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    const key = formatDate(d)
    const r = byDate.get(key)
    if (r) {
      logged += 1
      if (r.window_8h) windowOk += 1
      if (r.no_eating_after_8pm) noEight += 1
      if (r.exercised) exercised += 1
    }
    days.push({
      date: key,
      weekdayShort: WEEKDAY_SHORT[d.getDay()],
      window_8h: r ? Boolean(r.window_8h) : null,
      no_eating_after_8pm: r ? Boolean(r.no_eating_after_8pm) : null,
      exercised: r ? Boolean(r.exercised) : null,
      isToday: key === todayKey,
      isExerciseDay: isExerciseDay(d),
    })
  }

  return {
    days,
    rates: {
      window: logged ? Math.round((windowOk / logged) * 100) : null,
      noEight: logged ? Math.round((noEight / logged) * 100) : null,
      exerciseCount: exercised,
      loggedDays: logged,
    },
  }
}
