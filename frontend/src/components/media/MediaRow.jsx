import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import MediaCard from './MediaCard'
import { SkeletonCard } from '../ui/Skeleton'

const CARD_WIDTH = 'w-32 sm:w-36 md:w-40 shrink-0'

// Plex-style horizontal-scroll shelf used on the Home ("All") view.
export default function MediaRow({ title, items, seeAllHref, loading }) {
  if (!loading && (!items || items.length === 0)) return null

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
        {seeAllHref && (
          <Link
            to={seeAllHref}
            className="flex items-center gap-1 text-sm text-brand-600 dark:text-brand-400 hover:underline shrink-0"
          >
            See all <ChevronRight size={14} />
          </Link>
        )}
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-hide snap-x snap-mandatory">
        {loading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={`${CARD_WIDTH} snap-start`}>
                <SkeletonCard />
              </div>
            ))
          : items.map((item) => (
              <div key={item.id} className={`${CARD_WIDTH} snap-start`}>
                <MediaCard item={item} />
              </div>
            ))}
      </div>
    </section>
  )
}
