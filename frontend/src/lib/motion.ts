import type { Transition, Variants } from 'motion/react'

/** Shared entrance for a page section -- a quiet rise-and-settle, not a bounce. Every page
 * uses this once at its root so navigating between sections feels like one consistent
 * material moving, not per-component effects fighting each other. */
export const springy: Transition = { type: 'spring', stiffness: 300, damping: 30, mass: 0.6 }

export const pageEnter: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { ...springy, delay: 0.02 } },
}

/** Stagger a list's children in from a shared parent -- used for ranked lists, stat rows,
 * and table-like sequences so order is felt, not just read. */
export const listParent: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.045, delayChildren: 0.03 } },
}

export const listItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: springy },
}
