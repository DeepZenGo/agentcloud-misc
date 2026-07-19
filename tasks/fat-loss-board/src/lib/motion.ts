import { useReducedMotion } from 'motion/react'

export const springSoft = { type: 'spring' as const, bounce: 0, duration: 0.4 }
export const springSnap = { type: 'spring' as const, bounce: 0, duration: 0.3 }

export function useMotionSafe() {
  const reduced = useReducedMotion()
  return {
    reduced: Boolean(reduced),
    transition: reduced ? { duration: 0.2 } : springSoft,
    fadeOnly: reduced,
  }
}
