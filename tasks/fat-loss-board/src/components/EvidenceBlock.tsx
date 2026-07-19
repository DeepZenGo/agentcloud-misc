import { motion } from 'motion/react'
import { ExternalLink } from 'lucide-react'
import { useMotionSafe } from '../lib/motion'

const rows = [
  { group: '16:8 限时进食', fat: '−4.6%', waist: '−4.8 cm' },
  { group: '有氧运动（每周 3 次）', fat: '−3.5%', waist: '−4.6 cm' },
  { group: '联合干预', fat: '−10.2%', waist: '−7.5 cm', highlight: true },
]

export function EvidenceBlock() {
  const { transition, fadeOnly } = useMotionSafe()

  return (
    <section id="evidence" className="scroll-mt-20 px-4 py-12 pb-24">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">研究依据</h2>
        <p className="mt-2 max-w-2xl text-ink-muted">
          港中文 Nature Communications RCT（12 周）。灵活方案遵守率约 83–87%。
        </p>

        <div className="mt-8 space-y-4">
          {rows.map((r, i) => (
            <motion.div
              key={r.group}
              initial={fadeOnly ? { opacity: 0 } : { opacity: 0, y: 10 }}
              whileInView={fadeOnly ? { opacity: 1 } : { opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ ...transition, delay: fadeOnly ? 0 : i * 0.05 }}
              className={`flex flex-wrap items-baseline justify-between gap-3 border-b border-black/8 py-4 ${
                r.highlight ? 'text-teal' : 'text-ink'
              }`}
            >
              <span className={`text-[15px] ${r.highlight ? 'font-semibold' : ''}`}>{r.group}</span>
              <span className="font-mono text-sm tabular-nums">
                脂肪 {r.fat}
                <span className="mx-2 text-ink-muted">·</span>
                腰围 {r.waist}
              </span>
            </motion.div>
          ))}
        </div>

        <p className="mt-8 text-sm text-ink-muted">
          注意：原文热量减少约 −191 kcal/天（−801 kJ），不是 800 大卡。研究对象为 40–60
          岁超重/肥胖女性，机制可参考，人群有特化。
        </p>

        <a
          href="https://doi.org/10.1038/s41467-025-65678-z"
          target="_blank"
          rel="noreferrer"
          className="pressable mt-6 inline-flex min-h-11 items-center gap-2 text-sm font-medium text-teal"
        >
          DOI 10.1038/s41467-025-65678-z
          <ExternalLink className="size-4" aria-hidden />
        </a>
      </div>
    </section>
  )
}
