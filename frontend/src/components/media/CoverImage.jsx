import { useEffect, useState } from 'react'
import { BookOpen } from 'lucide-react'
import clsx from 'clsx'
import { coverProxyUrl } from '../../api/lookup'
import { CATEGORY_ICONS } from '../../lib/mediaIcons'

const CATEGORY_BG = {
  music: 'bg-rose-100 dark:bg-rose-900/30 text-rose-400',
  films_tv: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-400',
  books: 'bg-amber-100 dark:bg-amber-900/30 text-amber-400',
}

export default function CoverImage({ src, src2x, category, title, className, size = 'md' }) {
  const [error, setError] = useState(false)
  const Icon = CATEGORY_ICONS[category] || BookOpen

  // Reset a previous load failure when the source changes (e.g. a new cover
  // was uploaded) — otherwise this instance keeps showing the fallback icon
  // forever even once `src` points to a working image.
  useEffect(() => setError(false), [src, src2x])

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

  // Items whose cover hasn't been downloaded/optimised locally yet (or
  // never could be, e.g. a redirect-only host) fall back to the raw
  // third-party `cover_image_url` here — route those through the backend's
  // cover proxy so they load even when the client's own network/DNS can't
  // reach that host directly.
  const proxiedSrc = coverProxyUrl(src)
  const proxiedSrc2x = coverProxyUrl(src2x)

  return (
    <img
      src={proxiedSrc}
      srcSet={proxiedSrc2x && proxiedSrc2x !== proxiedSrc ? `${proxiedSrc} 1x, ${proxiedSrc2x} 2x` : undefined}
      alt={title}
      loading="lazy"
      decoding="async"
      onError={() => setError(true)}
      className={clsx('object-cover rounded-md', sizes[size], className)}
    />
  )
}
