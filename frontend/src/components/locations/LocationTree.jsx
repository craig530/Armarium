import { ChevronRight, ChevronDown, MapPin, Package } from 'lucide-react'
import { useState } from 'react'

function LocationNode({ loc, depth = 0, onSelect, selectedId }) {
  const [open, setOpen] = useState(depth < 2)
  const hasChildren = loc.children?.length > 0

  return (
    <div>
      <button
        onClick={() => {
          onSelect?.(loc)
          if (hasChildren) setOpen((o) => !o)
        }}
        className={`flex items-center gap-2 w-full text-left py-1.5 px-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
          selectedId === loc.id ? 'bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300' : ''
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          open ? <ChevronDown size={14} className="shrink-0 text-gray-400" /> : <ChevronRight size={14} className="shrink-0 text-gray-400" />
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        <MapPin size={14} className="shrink-0 text-gray-400" />
        <span className="text-sm font-medium text-gray-800 dark:text-gray-200 flex-1">{loc.name}</span>
        {loc.item_count > 0 && (
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <Package size={11} />
            {loc.item_count}
          </span>
        )}
      </button>
      {open && hasChildren && (
        <div>
          {loc.children.map((child) => (
            <LocationNode key={child.id} loc={child} depth={depth + 1} onSelect={onSelect} selectedId={selectedId} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function LocationTree({ locations, onSelect, selectedId }) {
  if (!locations.length) {
    return (
      <div className="text-sm text-gray-400 py-4 text-center">
        No locations yet. Create one to get started.
      </div>
    )
  }

  return (
    <div className="space-y-0.5">
      {locations.map((loc) => (
        <LocationNode key={loc.id} loc={loc} onSelect={onSelect} selectedId={selectedId} />
      ))}
    </div>
  )
}
