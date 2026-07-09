import type { ButtonHTMLAttributes } from 'react'
import { motion, useReducedMotion } from 'motion/react'

type Variant = 'primary' | 'secondary' | 'ghost'

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-accent-700 text-stone-50 hover:bg-accent-800 disabled:bg-accent-300 dark:bg-accent-600 dark:hover:bg-accent-500',
  secondary:
    'border border-stone-300 text-stone-800 hover:border-stone-400 hover:bg-stone-50 dark:border-stone-700 dark:text-stone-100 dark:hover:bg-stone-800',
  ghost: 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800',
}

// motion.button redefines a handful of DOM event handlers (onDrag and friends) with its own
// gesture-event signatures, which collide with the native HTMLButtonElement typings when
// spread -- omit them since this component never uses drag/animation callbacks itself.
type NativeButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart' | 'onAnimationEnd' | 'onAnimationIteration'
>

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: NativeButtonProps & { variant?: Variant }) {
  const reduceMotion = useReducedMotion()
  return (
    <motion.button
      {...props}
      whileTap={props.disabled ? undefined : { scale: reduceMotion ? 1 : 0.97 }}
      transition={{ duration: 0.12 }}
      className={`rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_CLASSES[variant]} ${className}`}
    />
  )
}
