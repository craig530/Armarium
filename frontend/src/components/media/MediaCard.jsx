import { useNavigate } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import { MediaTypeBadge } from '../ui/Badge'
import CoverImage from './CoverImage'

export default function MediaCard({ item }) {
  const navigate = useNavigate()
  const creator = item.artist || item.director || item.author

  return (
    <button
      onClick={() => navigate(`/item/${item.id}`)}
      className="group text-left w-full flex flex-col gap-2 rounded-xl p-3 hover:bg-white dark:hover:bg-gray-900 hover:shadow-md transition-all"
    >
      {/* Cover */}
      <div className="relative overflow-hidden rounded-lg aspect-[2/3] bg-gray-100 dark:bg-gray-800 w-full">
        {item.cover_url ? (
          <img
            src={item.cover_url}
            alt={item.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        ) : (
          <CoverImage type={item.media_type} title={item.title} size="full" />
        )}
        <div className="absolute top-2 left-2">
          <MediaTypeBadge type={item.media_type} />
        </div>
      </div>

      {/* Info */}
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{item.title}</p>
        {creator && <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{creator}</p>}
        {item.year && <p className="text-xs text-gray-400">{item.year}</p>}
        {item.location_path && (
          <div className="flex items-center gap-1 mt-1">
            <MapPin size={10} className="text-gray-400 shrink-0" />
            <span className="text-xs text-gray-400 truncate">{item.location_path}</span>
          </div>
        )}
      </div>
    </button>
  )
}
