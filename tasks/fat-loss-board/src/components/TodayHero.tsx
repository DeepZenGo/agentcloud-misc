import { motion } from 'motion/react'
import { Check, Circle, Flame, RefreshCw } from 'lucide-react'
import type { StatusResponse } from '../lib/types'
import { useMotionSafe } from '../lib/motion'

type Props = {
  status: StatusResponse
  onRefresh: () => void
  refreshing?: boolean
}

function CheckRow({
  label,
  value,
}: {
  label: string
  value: boolean | null
}) {
  const pending = value === null
  const ok = value === true
  return (
    <div className="flex min-h-11 items-center justify-between gap-4">
      <span className="text-[15px] text-ink">{label}</span>
      <span
        className={[
          'inline-flex items-center gap-1.5 text-sm font-medium',
          pending ? 'text-ink-muted' : ok ? 'text-teal' : 'text-warn',
        ].join(' ')}
      >
        {pending ? (
          <>
            <Circle className="size-4" aria-hidden />
            待打卡
          </>
        ) : ok ? (
          <>
            <Check className="size-4" aria-hidden />
            已完成
          </>
        ) : (
          <>
            <Circle className="size-4" aria-hidden />
            未达成
          </>
        )}
      </span>
    </div>
  )
}

function phaseClasses(phase: StatusResponse['today']['phase']) {
  switch (phase) {
    case 'eating':
      return { ring: 'stroke-teal', fill: 'text-teal', soft: 'bg-teal-soft' }
    case 'hard_cutoff':
      return { ring: 'stroke-warn', fill: 'text-warn', soft: 'bg-warn-soft' }
    case 'wind_down':
      return { ring: 'stroke-fast', fill: 'text-fast', soft: 'bg-fast-soft' }
    default:
      return { ring: 'stroke-fast', fill: 'text-fast', soft: 'bg-fast-soft' }
  }
}

export function TodayHero({ status, onRefresh, refreshing }: Props) {
  const { transition, fadeOnly } = useMotionSafe()
  const { today, streak, meta } = status
  const colors = phaseClasses(today.phase)
  const progress = meta.weekIndex / meta.totalWeeks
  const circumference = 2 * Math.PI * 54
  const dash = circumference * Math.min(1, Math.max(0, progress))

  return (
    <section id="today" className="scroll-mt-20 px-4 pb-10 pt-8">
      <div className="mx-auto max-w-3xl">
        <motion.div
          initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 16 }}
          animate={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
          transition={transition}
        >
          <p className="mb-2 text-sm font-medium tracking-wide text-ink-muted">
            第 {meta.weekIndex} / {meta.totalWeeks} 周
          </p>
          <h1 className="display-title text-ink">减脂作息</h1>
          <p className={`mt-4 text-xl font-semibold tracking-tight ${colors.fill}`}>
            现在 · {today.phaseLabel}
          </p>
          <p className="mt-2 max-w-xl text-[17px] text-ink-muted">{meta.mantra}</p>
        </motion.div>

        <div className="mt-10 flex flex-col items-center gap-10 sm:flex-row sm:items-start sm:justify-between">
          <motion.div
            className="relative grid place-items-center"
            initial={fadeOnly ? { opacity: 0 } : { opacity: 0, scale: 0.94 }}
            animate={fadeOnly ? { opacity: 1 } : { opacity: 1, scale: 1 }}
            transition={transition}
            aria-label={`12 周进度，第 ${meta.weekIndex} 周`}
          >
            <svg width="148" height="148" viewBox="0 0 148 148" className="-rotate-90">
              <circle
                cx="74"
                cy="74"
                r="54"
                fill="none"
                stroke="currentColor"
                strokeWidth="10"
                className="text-black/5"
              />
              <motion.circle
                cx="74"
                cy="74"
                r="54"
                fill="none"
                strokeWidth="10"
                strokeLinecap="round"
                className={colors.ring}
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: circumference - dash }}
                transition={transition}
              />
            </svg>
            <div className="absolute inset-0 grid place-items-center text-center">
              <div>
                <div className="flex items-center justify-center gap-1 text-teal">
                  <Flame className="size-5" aria-hidden />
                  <span className="text-3xl font-bold tracking-tight tabular-nums">
                    {streak}
                  </span>
                </div>
                <p className="text-xs text-ink-muted">连续天</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            className="w-full max-w-sm space-y-1"
            initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 12 }}
            animate={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ ...transition, delay: fadeOnly ? 0 : 0.06 }}
          >
            <CheckRow label="进食窗口在 8h 内" value={today.window_8h} />
            <CheckRow label="晚 8 点后没吃" value={today.no_eating_after_8pm} />
            <CheckRow
              label={today.isExerciseDay ? '今日运动（计划日）' : '今日运动'}
              value={today.exercised}
            />
            {today.note ? (
              <p className="pt-2 text-sm text-ink-muted">备注：{today.note}</p>
            ) : null}
          </motion.div>
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          <a
            href="#timeline"
            className="pressable inline-flex min-h-11 items-center justify-center rounded-full bg-teal px-6 text-[15px] font-semibold text-white"
          >
            查看今日日程
          </a>
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="pressable glass inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-full px-5 text-[15px] font-medium text-ink disabled:opacity-60"
          >
            <RefreshCw className={`size-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden />
            刷新
          </button>
        </div>
      </div>
    </section>
  )
}
