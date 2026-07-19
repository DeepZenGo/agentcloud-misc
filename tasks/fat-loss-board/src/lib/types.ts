export type Phase = 'fasting' | 'eating' | 'hard_cutoff' | 'wind_down'

export type DayLog = {
  date: string
  weekday?: string
  window_8h?: boolean
  no_eating_after_8pm?: boolean
  exercised?: boolean
  note?: string
  timestamp?: string
}

export type ScheduleItem = {
  time: string
  label: string
  kind: 'fasting' | 'eating' | 'exercise' | 'checkin' | 'sleep'
  exerciseOnly?: boolean
}

export type StatusResponse = {
  today: {
    date: string
    phase: Phase
    phaseLabel: string
    window_8h: boolean | null
    no_eating_after_8pm: boolean | null
    exercised: boolean | null
    note?: string
    isExerciseDay: boolean
  }
  streak: number
  week: {
    days: Array<{
      date: string
      weekdayShort: string
      window_8h: boolean | null
      no_eating_after_8pm: boolean | null
      exercised: boolean | null
      isToday: boolean
      isExerciseDay: boolean
    }>
    rates: {
      window: number | null
      noEight: number | null
      exerciseCount: number
      loggedDays: number
    }
  }
  schedule: ScheduleItem[]
  meta: {
    startDate: string
    weekIndex: number
    totalWeeks: number
    mantra: string
  }
  now: string
}
