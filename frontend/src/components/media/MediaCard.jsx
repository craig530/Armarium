import { useNavigate } from 'react-router-dom'
import { Star } from 'lucide-react'
import { MediaSubtypeIcon, OwnershipIcon } from '../ui/Badge'
import CoverImage from './CoverImage'
import OwnershipRow from './OwnershipRow'

export default function MediaCard({ item }) {
  const navigate = useNavigate()
  const creator = item.artist || item.director || item.author

  return (
    <button
      onClick={() => navigate(`/item/${item.id}`)}
      className="group text-left w-full flex flex-col gap-2 rounded-xl p-3 hover:bg-white dark:hover:bg-gray-900 hover:shadow-md transition-all"
    >
      {/* Cover — square for music (album art), portrait for everything else */}
      <div className={`relative overflow-hidden rounded-lg ${item.category === 'music' ? 'aspect-square' : 'aspect-2/3'} bg-gray-100 dark:bg-gray-800 w-full`}>
        <CoverImage
          src={item.cover_thumb_url}
          src2x={item.cover_url}
          category={item.category}
          title={item.title}
          size="full"
          className="group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute top-2 left-2">
          <MediaSubtypeIcon subtype={item.media_subtype} className="shadow-xs" />
        </div>
        <div className="absolute top-2 right-2">
          <OwnershipIcon ownership={item.ownership} className="shadow-xs" />
        </div>
        {/* Rating strip — starts below the top-left badge to avoid overlap */}
        {item.user_rating > 0 && (
          <div className="absolute left-0 top-9 bottom-0 w-5 flex flex-col items-center justify-end pb-2 gap-px bg-gradient-to-r from-black/50 to-transparent pointer-events-none">
            {Array.from({ length: item.user_rating }).map((_, i) => (
              <Star key={i} size={8} fill="#facc15" className="text-yellow-400 shrink-0" />
            ))}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{item.title}</p>
        {creator && <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{creator}</p>}
        {item.year && <p className="text-xs text-gray-400">{item.year}</p>}
        <OwnershipRow item={item} className="mt-1" />
      </div>
    </button>
  )
}
