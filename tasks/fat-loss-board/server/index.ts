import express from 'express'
import cors from 'cors'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
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

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DIST = path.resolve(__dirname, '../dist')

const LOG_FILE =
  process.env.HABIT_LOG_FILE ||
  path.join(os.homedir(), '.hermes', 'habit-track', 'daily-log.json')

const PORT = Number(process.env.PORT || 8787)
const HOST = process.env.HOST || '0.0.0.0'
const SERVE_STATIC = process.env.SERVE_STATIC === '1' || process.argv.includes('--static')

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

function tailscaleIPv4(): string | null {
  try {
    const ifaces = os.networkInterfaces()
    for (const list of Object.values(ifaces)) {
      for (const info of list ?? []) {
        if (info.family === 'IPv4' && info.address.startsWith('100.')) {
          return info.address
        }
      }
    }
  } catch {
    /* ignore */
  }
  return null
}

const app = express()
app.use(cors())

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, logFile: LOG_FILE, static: SERVE_STATIC && fs.existsSync(DIST) })
})

app.get('/api/status', (_req, res) => {
  res.json(buildStatus())
})

if (SERVE_STATIC) {
  if (!fs.existsSync(DIST)) {
    console.error(`[fat-loss-board] dist/ missing — run npm run build first`)
    process.exit(1)
  }
  app.use(express.static(DIST, { index: 'index.html' }))
  app.use((req, res, next) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') return next()
    if (req.path.startsWith('/api')) return next()
    res.sendFile(path.join(DIST, 'index.html'))
  })
}

app.listen(PORT, HOST, () => {
  const ts = tailscaleIPv4()
  console.log(`[fat-loss-board] listening on http://${HOST}:${PORT}`)
  console.log(`[fat-loss-board] local     http://127.0.0.1:${PORT}`)
  if (ts) console.log(`[fat-loss-board] tailscale http://${ts}:${PORT}`)
  console.log(`[fat-loss-board] log       ${LOG_FILE}`)
  if (SERVE_STATIC) console.log(`[fat-loss-board] static    ${DIST}`)
})
