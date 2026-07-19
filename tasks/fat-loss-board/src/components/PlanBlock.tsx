import { motion } from 'motion/react'
import { useMotionSafe } from '../lib/motion'

const mantras = [
  '最好的方案，是最不容易放弃的方案',
  '80% 做到就够了，20% 不焦虑',
  '不是人配合方案，是方案配合人',
]

export function PlanBlock() {
  const { transition, fadeOnly } = useMotionSafe()

  return (
    <section id="plan" className="scroll-mt-20 px-4 py-12">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">方案</h2>
        <p className="mt-2 text-ink-muted">灵活 16:8 + 每周三次有氧</p>

        <motion.div
          initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 12 }}
          whileInView={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={transition}
          className="mt-8"
        >
          <p className="text-sm font-medium uppercase tracking-wider text-warn">唯一死规矩</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
            晚 8 点后不吃
          </p>
          <p className="mt-3 max-w-lg text-[15px] text-ink-muted">
            窗口可灵活调整；一三五快走/慢跑约 35 分钟，其余日休息或补练。
          </p>
        </motion.div>

        <ul className="mt-10 space-y-6">
          {mantras.map((m, i) => (
            <motion.li
              key={m}
              initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 10 }}
              whileInView={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ ...transition, delay: fadeOnly ? 0 : i * 0.05 }}
              className="border-l-2 border-teal/40 pl-4 text-lg tracking-tight text-ink"
            >
              {m}
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  )
}
