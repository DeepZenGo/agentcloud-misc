import { motion } from 'motion/react'
import { Check, Minus, X } from 'lucide-react'
import type { StatusResponse } from '../lib/types'
import { useMotionSafe } from '../lib/motion'

type Props = { status: StatusResponse }

function Cell({ value }: { value: boolean | null }) {
  if (value === null) {
    return (
      <span className="inline-flex size-8 items-center justify-center text-ink-muted" aria-label="无记录">
        <Minus className="size-4" />
      </span>
    )
  }
  if (value) {
    return (
      <span className="inline-flex size-8 items-center justify-center text-teal" aria-label="完成">
        <Check className="size-4" />
      </span>
    )
  }
  return (
    <span className="inline-flex size-8 items-center justify-center text-warn" aria-label="未达成">
      <X className="size-4" />
    </span>
  )
}

export function WeekGrid({ status }: Props) {
  const { transition, fadeOnly } = useMotionSafe()
  const { days, rates } = status.week

  return (
    <section id="week" className="scroll-mt-20 px-4 py-12">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">本周</h2>
        <p className="mt-2 text-ink-muted">
          已记录 {rates.loggedDays} 天
          {rates.window !== null ? ` · 窗口 ${rates.window}%` : ''}
          {rates.noEight !== null ? ` · 晚8 ${rates.noEight}%` : ''}
          {` · 运动 ${rates.exerciseCount} 次`}
        </p>

        <div className="mt-8 overflow-x-auto">
          <table className="w-full min-w-[320px] border-collapse text-center text-sm">
            <thead>
              <tr className="text-ink-muted">
                <th className="pb-3 text-left font-medium">日</th>
                {days.map((d) => (
                  <th
                    key={d.date}
                    className={`pb-3 font-medium ${d.isToday ? 'text-teal' : ''}`}
                  >
                    {d.weekdayShort}
                    {d.isExerciseDay ? (
                      <span className="mt-0.5 block text-[10px] font-normal">运</span>
                    ) : (
                      <span className="mt-0.5 block text-[10px] font-normal opacity-0">运</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(
                [
                  ['窗口', 'window_8h'],
                  ['晚8', 'no_eating_after_8pm'],
                  ['运动', 'exercised'],
                ] as const
              ).map(([label, key], row) => (
                <motion.tr
                  key={key}
                  initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 8 }}
                  whileInView={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ ...transition, delay: fadeOnly ? 0 : row * 0.05 }}
                >
                  <th className="py-2 text-left font-medium text-ink">{label}</th>
                  {days.map((d) => (
                    <td key={`${d.date}-${key}`} className="py-2">
                      <div className="flex justify-center">
                        <Cell value={d[key]} />
                      </div>
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
