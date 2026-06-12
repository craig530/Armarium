import logoUrl from '../../assets/brand/armarium-logo.svg'

// The Armarium mark: a leather-brown rounded badge with a cream archive/
// bookshelf glyph. Self-contained colours, so it reads the same in light
// and dark mode.
export default function Logo({ size = 32, withWordmark = false, wordmarkClassName = '', className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <img src={logoUrl} alt="Armarium" width={size} height={size} className="rounded-lg shrink-0" />
      {withWordmark && (
        <span className={`font-display font-semibold tracking-tight text-gray-900 dark:text-white ${wordmarkClassName}`}>
          Armarium
        </span>
      )}
    </span>
  )
}
