import { motion } from 'motion/react'
import type { StatusResponse } from '../lib/types'
import { activeScheduleIndex } from '../lib/phase'
import { useMotionSafe } from '../lib/motion'

type Props = { status: StatusResponse }

export function DayTimeline({ status }: Props) {
  const { transition, fadeOnly } = useMotionSafe()
  const active = activeScheduleIndex(new Date(status.now))
  const items = status.schedule.filter(
    (item) => !(item.exerciseOnly && !status.today.isExerciseDay),
  )

  // Remap active index after filter
  const full = status.schedule
  const activeTime = full[active]?.time
  const activeFiltered = items.findIndex((i) => i.time === activeTime)

  return (
    <section id="timeline" className="scroll-mt-20 px-4 py-12">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">今日日程</h2>
        <p className="mt-2 text-ink-muted">16:8 灵活窗口 · 晚 8 点后不吃是唯一死规矩</p>

        <ol className="relative mt-8 space-y-0">
          {items.map((item, i) => {
            const isActive = i === activeFiltered
            const kindColor =
              item.kind === 'eating'
                ? 'bg-teal'
                : item.kind === 'exercise'
                  ? 'bg-warn'
                  : item.kind === 'checkin'
                    ? 'bg-teal'
                    : 'bg-fast'

            return (
              <motion.li
                key={`${item.time}-${item.label}`}
                initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 10 }}
                whileInView={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ ...transition, delay: fadeOnly ? 0 : i * 0.03 }}
                className="relative flex gap-4 pb-6 last:pb-0"
              >
                <div className="flex w-14 shrink-0 flex-col items-end pt-0.5">
                  <span
                    className={`font-mono text-sm tabular-nums ${
                      isActive ? 'font-semibold text-teal' : 'text-ink-muted'
                    }`}
                  >
                    {item.time}
                  </span>
                </div>
                <div className="relative flex flex-col items-center">
                  <span
                    className={`mt-1.5 size-2.5 rounded-full ${kindColor} ${
                      isActive ? 'ring-4 ring-teal/20' : ''
                    }`}
                    aria-hidden
                  />
                  {i < items.length - 1 ? (
                    <span className="mt-1 w-px flex-1 bg-black/10" aria-hidden />
                  ) : null}
                </div>
                <div
                  className={`min-h-11 flex-1 rounded-2xl px-4 py-3 ${
                    isActive ? 'bg-white/70 shadow-sm' : ''
                  }`}
                >
                  <p className={`text-[15px] ${isActive ? 'font-semibold text-ink' : 'text-ink'}`}>
                    {item.label}
                    {isActive ? (
                      <span className="ml-2 text-xs font-medium text-teal">当前</span>
                    ) : null}
                  </p>
                </div>
              </motion.li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
