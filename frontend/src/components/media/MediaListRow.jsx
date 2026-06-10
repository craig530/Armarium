import { useNavigate } from 'react-router-dom'
import { MapPin, MoreVertical } from 'lucide-react'
import { MediaTypeBadge } from '../ui/Badge'
import CoverImage from './CoverImage'
import { useState } from 'react'
import { mediaApi } from '../../api/media'
import toast from 'react-hot-toast'

export default function MediaListRow({ item, onDeleted }) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const creator = item.artist || item.director || item.author

  const handleDelete = async (e) => {
    e.stopPropagation()
    if (!confirm(`Delete "${item.title}"?`)) return
    try {
      await mediaApi.delete(item.id)
      toast.success('Item deleted')
      onDeleted?.(item.id)
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div
      onClick={() => navigate(`/item/${item.id}`)}
      className="flex items-center gap-4 p-3 rounded-xl hover:bg-white dark:hover:bg-gray-900 hover:shadow-sm transition-all cursor-pointer group"
    >
      {/* Cover thumbnail */}
      <div className="shrink-0 h-16 w-12 rounded-md overflow-hidden bg-gray-100 dark:bg-gray-800">
        {item.cover_url ? (
          <img src={item.cover_url} alt={item.title} className="h-full w-full object-cover" />
        ) : (
          <CoverImage type={item.media_type} title={item.title} size="sm" className="h-full w-full" />
        )}
      </div>

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-2">
          <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{item.title}</p>
          <MediaTypeBadge type={item.media_type} className="shrink-0" />
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
          {[creator, item.year].filter(Boolean).join(' · ')}
        </p>
        {item.edition && <p className="text-xs text-gray-400">{item.edition}</p>}
      </div>

      {/* Location */}
      {item.location_path && (
        <div className="hidden md:flex items-center gap-1 shrink-0 max-w-[180px]">
          <MapPin size={12} className="text-gray-400 shrink-0" />
          <span className="text-xs text-gray-400 truncate">{item.location_path}</span>
        </div>
      )}

      {/* Actions */}
      <div className="relative shrink-0" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
        >
          <MoreVertical size={16} />
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 z-20 mt-1 w-36 rounded-lg bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700 py-1">
              <button
                onClick={() => { navigate(`/item/${item.id}`); setMenuOpen(false) }}
                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Edit
              </button>
              <button
                onClick={handleDelete}
                className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                Delete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
