import { useState } from 'react'
import { Star } from 'lucide-react'
import clsx from 'clsx'

// Interactive when `onChange` is provided; otherwise renders a smaller,
// read-only display of `value` (clicking re-selects the current rating to
// clear it, since 0 isn't a valid `user_rating`).
export default function StarRating({ value, onChange, size, className }) {
  const [hover, setHover] = useState(null)
  const readOnly = !onChange
  const iconSize = size ?? (readOnly ? 14 : 20)
  const display = hover ?? value ?? 0

  return (
    <div className={clsx('inline-flex items-center gap-0.5', className)}>
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= display
        const Tag = readOnly ? 'span' : 'button'
        return (
          <Tag
            key={star}
            type={readOnly ? undefined : 'button'}
            aria-label={readOnly ? undefined : `Rate ${star} star${star === 1 ? '' : 's'}`}
            onClick={readOnly ? undefined : () => onChange(star === value ? null : star)}
            onMouseEnter={readOnly ? undefined : () => setHover(star)}
            onMouseLeave={readOnly ? undefined : () => setHover(null)}
            className={clsx(
              filled ? 'text-amber-400' : 'text-gray-300 dark:text-gray-600',
              !readOnly && 'cursor-pointer hover:scale-110 transition-transform'
            )}
          >
            <Star size={iconSize} fill={filled ? 'currentColor' : 'none'} />
          </Tag>
        )
      })}
    </div>
  )
}
