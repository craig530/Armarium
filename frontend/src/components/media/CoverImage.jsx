import { useState } from 'react'
import { Music, Clapperboard, BookOpen } from 'lucide-react'
import clsx from 'clsx'

const CATEGORY_ICONS = { music: Music, films_tv: Clapperboard, books: BookOpen }
const CATEGORY_BG = {
  music: 'bg-rose-100 dark:bg-rose-900/30 text-rose-400',
  films_tv: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-400',
  books: 'bg-amber-100 dark:bg-amber-900/30 text-amber-400',
}

export default function CoverImage({ src, src2x, category, title, className, size = 'md' }) {
  const [error, setError] = useState(false)
  const Icon = CATEGORY_ICONS[category] || BookOpen

  const sizes = {
    sm: 'h-16 w-12',
    md: 'h-44 w-32',
    lg: 'h-64 w-48',
    full: 'h-full w-full',
  }
  const iconSizes = { sm: 20, md: 40, lg: 56, full: 40 }

  if (!src || error) {
    return (
      <div className={clsx('flex items-center justify-center rounded-md', CATEGORY_BG[category] || CATEGORY_BG.books, sizes[size], className)}>
        <Icon size={iconSizes[size]} />
      </div>
    )
  }

  return (
    <img
      src={src}
      srcSet={src2x && src2x !== src ? `${src} 1x, ${src2x} 2x` : undefined}
      alt={title}
      loading="lazy"
      onError={() => setError(true)}
      className={clsx('object-cover rounded-md', sizes[size], className)}
    />
  )
}
