import type { Phase, ScheduleItem } from './types'

/** Minutes from midnight */
export function minutesOfDay(d: Date = new Date()): number {
  return d.getHours() * 60 + d.getMinutes()
}

export function parseHHMM(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}

/** Mon=1 … Sun=0 or 7 → exercise on Mon/Wed/Fri (1,3,5) */
export function isExerciseDay(d: Date = new Date()): boolean {
  const day = d.getDay() // 0 Sun … 6 Sat
  return day === 1 || day === 3 || day === 5
}

/**
 * Timeline from plan:
 * 10:00 eating opens → ~18:00 window closes → 20:00 hard cutoff → 21:00+ wind down
 * Outside eating = fasting (before 10 and after ~18 until wind_down nuance)
 */
export function computePhase(now: Date = new Date()): Phase {
  const mins = minutesOfDay(now)
  const open = parseHHMM('10:00')
  const close = parseHHMM('18:00')
  const hard = parseHHMM('20:00')
  const wind = parseHHMM('21:00')

  if (mins >= open && mins < close) return 'eating'
  if (mins >= hard && mins < wind) return 'hard_cutoff'
  if (mins >= wind) return 'wind_down'
  // 18:00–20:00 still fasting period after window
  return 'fasting'
}

export function phaseLabel(phase: Phase): string {
  switch (phase) {
    case 'eating':
      return '进食窗口'
    case 'hard_cutoff':
      return '晚8硬截止'
    case 'wind_down':
      return '睡前收束'
    case 'fasting':
    default:
      return '禁食期'
  }
}

export const SCHEDULE: ScheduleItem[] = [
  { time: '07:00', label: '起床 · 喝温水', kind: 'fasting' },
  { time: '07:30', label: '黑咖啡 / 水 / 茶', kind: 'fasting' },
  { time: '08:00', label: '开始工作', kind: 'fasting' },
  { time: '10:00', label: '第一餐 · 窗口开启', kind: 'eating' },
  { time: '12:00', label: '午餐', kind: 'eating' },
  { time: '17:00', label: '最后一餐', kind: 'eating' },
  { time: '18:00', label: '窗口关闭 · 禁食开始', kind: 'fasting' },
  { time: '18:30', label: '快走 / 慢跑 35 分钟', kind: 'exercise', exerciseOnly: true },
  { time: '20:00', label: '晚8硬截止', kind: 'fasting' },
  { time: '21:00', label: '睡前打卡', kind: 'checkin' },
  { time: '22:30', label: '准备睡觉', kind: 'sleep' },
  { time: '23:00', label: '熄灯', kind: 'sleep' },
]

export function activeScheduleIndex(now: Date = new Date()): number {
  const mins = minutesOfDay(now)
  let idx = 0
  for (let i = 0; i < SCHEDULE.length; i++) {
    if (mins >= parseHHMM(SCHEDULE[i].time)) idx = i
  }
  return idx
}

export const START_DATE = '2026-07-19'
export const TOTAL_WEEKS = 12

export function weekIndex(now: Date = new Date(), start = START_DATE): number {
  const startMs = Date.parse(`${start}T00:00:00`)
  const days = Math.floor((now.getTime() - startMs) / 86_400_000)
  if (days < 0) return 1
  return Math.min(TOTAL_WEEKS, Math.floor(days / 7) + 1)
}

export const MANTRAS = [
  '最好的方案，是最不容易放弃的方案',
  '80% 做到就够了，20% 不焦虑',
  '不是人配合方案，是方案配合人',
] as const

export function mantraForDay(now: Date = new Date()): string {
  const day = Math.floor(now.getTime() / 86_400_000)
  return MANTRAS[day % MANTRAS.length]
}
