import express from 'express'
import cors from 'cors'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import type { DayLog, StatusResponse } from '../src/lib/types.ts'
import {
  SCHEDULE,
  START_DATE,
  TOTAL_WEEKS,
  computePhase,
  isExerciseDay,
  mantraForDay,
  phaseLabel,
  weekIndex,
} from '../src/lib/phase.ts'
import { computeStreak, formatDate, weekSummary } from '../src/lib/stats.ts'

const LOG_FILE =
  process.env.HABIT_LOG_FILE ||
  path.join(os.homedir(), '.hermes', 'habit-track', 'daily-log.json')

const PORT = Number(process.env.PORT || 8787)

function loadLogs(): DayLog[] {
  try {
    if (!fs.existsSync(LOG_FILE)) return []
    const raw = fs.readFileSync(LOG_FILE, 'utf8')
    const data = JSON.parse(raw) as DayLog[]
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

function buildStatus(now = new Date()): StatusResponse {
  const records = loadLogs()
  const todayKey = formatDate(now)
  const todayRec = records.find((r) => r.date === todayKey)
  const phase = computePhase(now)
  const week = weekSummary(records, now)

  return {
    today: {
      date: todayKey,
      phase,
      phaseLabel: phaseLabel(phase),
      window_8h: todayRec ? Boolean(todayRec.window_8h) : null,
      no_eating_after_8pm: todayRec ? Boolean(todayRec.no_eating_after_8pm) : null,
      exercised: todayRec ? Boolean(todayRec.exercised) : null,
      note: todayRec?.note,
      isExerciseDay: isExerciseDay(now),
    },
    streak: computeStreak(records),
    week,
    schedule: SCHEDULE,
    meta: {
      startDate: START_DATE,
      weekIndex: weekIndex(now),
      totalWeeks: TOTAL_WEEKS,
      mantra: mantraForDay(now),
    },
    now: now.toISOString(),
  }
}

const app = express()
app.use(cors())

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, logFile: LOG_FILE })
})

app.get('/api/status', (_req, res) => {
  res.json(buildStatus())
})

app.listen(PORT, () => {
  console.log(`[fat-loss-board] API http://127.0.0.1:${PORT}`)
  console.log(`[fat-loss-board] log  ${LOG_FILE}`)
})
