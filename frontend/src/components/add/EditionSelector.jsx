import { ChevronRight } from 'lucide-react'
import { MediaSubtypeBadge } from '../ui/Badge'
import { categoryLabel } from '../../lib/categories'
import Button from '../ui/Button'

export default function EditionSelector({ candidates, onSelect, onBack }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ChevronRight size={18} className="rotate-180" />
        </Button>
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Select edition</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">{candidates.length} result{candidates.length !== 1 ? 's' : ''} found</p>
        </div>
      </div>

      <div className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto pr-1">
        {candidates.map((c, i) => (
          <button
            key={`${c.external_id}-${i}`}
            onClick={() => onSelect(c)}
            className="flex items-start gap-3 p-3 rounded-xl text-left hover:bg-white dark:hover:bg-gray-800 hover:shadow-md transition-all border border-transparent hover:border-gray-200 dark:hover:border-gray-700"
          >
            {/* Cover thumbnail */}
            <div className="shrink-0 h-20 w-14 rounded-md overflow-hidden bg-gray-100 dark:bg-gray-800">
              {c.cover_url ? (
                <img src={c.cover_url} alt={c.title} className="h-full w-full object-cover" onError={(e) => { e.target.style.display='none' }} />
              ) : (
                <div className="h-full w-full flex items-center justify-center text-gray-400 text-2xl">?</div>
              )}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start gap-2 flex-wrap">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{c.title}</p>
                <MediaSubtypeBadge subtype={{ category: c.category, name: categoryLabel(c.category) }} />
              </div>
              {c.creator && <p className="text-xs text-gray-500 dark:text-gray-400">{c.creator}</p>}
              {c.year && <p className="text-xs text-gray-400">{c.year}</p>}
              {c.edition && (
                <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  {c.edition}
                </span>
              )}
              <p className="text-xs text-gray-300 dark:text-gray-600 mt-1 capitalize">via {c.source}</p>
            </div>

            <ChevronRight size={16} className="shrink-0 text-gray-400 mt-1" />
          </button>
        ))}
      </div>
    </div>
  )
}
