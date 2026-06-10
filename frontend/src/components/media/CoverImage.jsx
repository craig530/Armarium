import { useState } from 'react'
import { Music, Film, BookOpen, Disc } from 'lucide-react'
import clsx from 'clsx'

const TYPE_ICONS = { cd: Music, dvd: Film, bluray: Disc, book: BookOpen }
const TYPE_BG = {
  cd: 'bg-purple-100 dark:bg-purple-900/30 text-purple-400',
  dvd: 'bg-blue-100 dark:bg-blue-900/30 text-blue-400',
  bluray: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-400',
  book: 'bg-amber-100 dark:bg-amber-900/30 text-amber-400',
}

export default function CoverImage({ src, type, title, className, size = 'md' }) {
  const [error, setError] = useState(false)
  const Icon = TYPE_ICONS[type] || BookOpen

  const sizes = {
    sm: 'h-16 w-12',
    md: 'h-44 w-32',
    lg: 'h-64 w-48',
    full: 'h-full w-full',
  }
  const iconSizes = { sm: 20, md: 40, lg: 56, full: 40 }

  if (!src || error) {
    return (
      <div className={clsx('flex items-center justify-center rounded-md', TYPE_BG[type], sizes[size], className)}>
        <Icon size={iconSizes[size]} />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={title}
      onError={() => setError(true)}
      className={clsx('object-cover rounded-md', sizes[size], className)}
    />
  )
}
