import { motion } from 'motion/react'
import { useMotionSafe } from '../lib/motion'

const links = [
  { href: '#today', label: '今日' },
  { href: '#timeline', label: '日程' },
  { href: '#week', label: '本周' },
  { href: '#plan', label: '方案' },
  { href: '#evidence', label: '研究' },
]

export function GlassNav() {
  const { transition } = useMotionSafe()

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={transition}
      className="glass sticky top-0 z-40 border-x-0 border-t-0"
    >
      <nav
        aria-label="页面分区"
        className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3"
      >
        <a
          href="#today"
          className="pressable min-h-11 min-w-11 inline-flex items-center text-sm font-semibold tracking-tight text-ink"
        >
          减脂作息
        </a>
        <ul className="flex items-center gap-1 overflow-x-auto">
          {links.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="pressable inline-flex min-h-11 items-center rounded-full px-3 text-sm text-ink-muted hover:text-ink"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </motion.header>
  )
}
