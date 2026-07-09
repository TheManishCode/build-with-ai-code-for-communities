/** The constituency mark -- a survey/boundary-stone notch inside a register seal, standing
 * in for a wordmark logo. Two ticks at the top read as a surveyor's benchmark cut; the
 * offset inner dot reads as a stamp impression. Deliberately not an icon-in-a-box. */
export function Mark({ size = 34, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" fill="none" className={className} aria-hidden="true">
      <circle cx="17" cy="17" r="15.5" stroke="currentColor" strokeOpacity="0.85" strokeWidth="1.4" />
      <path d="M13 6.5 L13 11 M21 6.5 L21 11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="15.5" cy="19" r="4.75" fill="currentColor" />
    </svg>
  )
}
