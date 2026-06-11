import { useState } from 'react'
import { Music, Clapperboard, BookOpen } from 'lucide-react'
import clsx from 'clsx'

const CATEGORY_ICONS = { music: Music, films_tv: Clapperboard, books: BookOpen }
const CATEGORY_BG = {
  music: 'bg-purple-100 dark:bg-purple-900/30 text-purple-400',
  films_tv: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-400',
  books: 'bg-amber-100 dark:bg-amber-900/30 text-amber-400',
}

export default function CoverImage({ src, category, title, className, size = 'md' }) {
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
      alt={title}
      loading="lazy"
      onError={() => setError(true)}
      className={clsx('object-cover rounded-md', sizes[size], className)}
    />
  )
}
