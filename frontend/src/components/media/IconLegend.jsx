import { OwnershipIcon } from '../ui/Badge'
import { getSubtypeIcon, OWNERSHIP_LABELS } from '../../lib/mediaIcons'

// Explains the small subtype/ownership icons shown on media cards and rows —
// one entry per distinct format icon actually present in `items`, so the
// legend always matches what's on screen (e.g. a Books page explains the
// Book/Graphic Novel/eBook/Audiobook icons, not an unrelated CD disc).
export default function IconLegend({ items = [] }) {
  const formats = []
  const seen = new Set()
  for (const item of items) {
    const Icon = getSubtypeIcon(item.media_subtype)
    if (!Icon || seen.has(Icon)) continue
    seen.add(Icon)
    formats.push({ Icon, label: item.media_subtype.name })
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-gray-400">
      {formats.map(({ Icon, label }) => (
        <span key={label} className="flex items-center gap-1.5">
          <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            <Icon size={14} />
          </span>
          {label}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <OwnershipIcon ownership="physical" />
        {OWNERSHIP_LABELS.physical}
      </span>
      <span className="flex items-center gap-1.5">
        <OwnershipIcon ownership="digital" />
        {OWNERSHIP_LABELS.digital}
      </span>
    </div>
  )
}
