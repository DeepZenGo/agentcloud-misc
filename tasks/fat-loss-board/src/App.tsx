import { useCallback, useEffect, useState } from 'react'
import { fetchStatus } from './api'
import type { StatusResponse } from './lib/types'
import { GlassNav } from './components/GlassNav'
import { TodayHero } from './components/TodayHero'
import { DayTimeline } from './components/DayTimeline'
import { WeekGrid } from './components/WeekGrid'
import { PlanBlock } from './components/PlanBlock'
import { EvidenceBlock } from './components/EvidenceBlock'

export default function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true)
    try {
      const data = await fetchStatus()
      setStatus(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(true), 60_000)
    const onVis = () => {
      if (document.visibilityState === 'visible') void load(true)
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [load])

  return (
    <div className="min-h-dvh">
      <GlassNav />
      <main>
        {error && !status ? (
          <div className="mx-auto max-w-3xl px-4 py-20 text-center">
            <p className="text-lg text-ink">无法连接本地 API</p>
            <p className="mt-2 text-sm text-ink-muted">
              请确认已运行 <code className="font-mono">npm run dev</code>（含 API 服务）。
              {error ? ` (${error})` : ''}
            </p>
            <button
              type="button"
              onClick={() => void load()}
              className="pressable mt-6 inline-flex min-h-11 cursor-pointer items-center rounded-full bg-teal px-6 text-sm font-semibold text-white"
            >
              重试
            </button>
          </div>
        ) : null}

        {status ? (
          <>
            <TodayHero
              status={status}
              onRefresh={() => void load()}
              refreshing={refreshing}
            />
            <DayTimeline status={status} />
            <WeekGrid status={status} />
            <PlanBlock />
            <EvidenceBlock />
          </>
        ) : !error ? (
          <div className="mx-auto max-w-3xl px-4 py-24 text-ink-muted">加载中…</div>
        ) : null}
      </main>
    </div>
  )
}
