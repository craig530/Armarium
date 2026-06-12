import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import CoverImage from '../media/CoverImage'
import { MediaSubtypeIcon, OwnershipIcon } from '../ui/Badge'

// Shows the in-progress batch session list (most-recent-first) or, outside
// batch mode, the 10 most-recently-added library items — both as a tappable
// list that opens the edit modal. Collapsed by default on narrow screens so
// it never pushes the scanner viewfinder/buttons off-screen on small
// devices; expanded by default on larger screens.
export default function ItemListPanel({ title, items, onItemClick }) {
  const [expanded, setExpanded] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 640)

  if (!items.length) return null

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        <span>{title} ({items.length})</span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {expanded && (
        <div className="flex flex-col gap-1 border-t border-gray-100 dark:border-gray-800 p-2 max-h-72 overflow-y-auto">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onItemClick(item)}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-left"
            >
              <CoverImage
                src={item.cover_thumb_url}
                src2x={item.cover_url}
                category={item.category}
                title={item.title}
                size="sm"
                className="h-12 w-9 shrink-0"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate min-w-0">{item.title}</p>
                  <MediaSubtypeIcon subtype={item.media_subtype} className="shrink-0" />
                </div>
                <p className="text-xs text-gray-400 truncate">
                  {item.location_path || item.platform?.name || ''}
                </p>
              </div>
              <OwnershipIcon ownership={item.ownership} className="shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
