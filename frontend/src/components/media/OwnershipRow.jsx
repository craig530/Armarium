import { Tv } from 'lucide-react'
import clsx from 'clsx'
import LocationIcon from '../ui/LocationIcon'
import { platformLogoUrl } from '../../lib/platformLogos'

function IconBox({ children }) {
  return (
    <span className="shrink-0 h-5 w-5 rounded-sm bg-white dark:bg-gray-900 flex items-center justify-center p-0.5">
      {children}
    </span>
  )
}

function LocationChip({ record }) {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 min-w-0 max-w-full">
      <IconBox>
        <LocationIcon
          location={{ icon_key: record.location_icon_key, icon_url: record.location_icon_url }}
          size={12}
        />
      </IconBox>
      <span className="truncate">{record.location_path || record.location_name || 'No location'}</span>
    </span>
  )
}

function PlatformChip({ record }) {
  const url = platformLogoUrl(record.platform)
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 min-w-0 max-w-full">
      <IconBox>
        {url ? <img src={url} alt="" className="h-full w-full object-contain" /> : <Tv size={12} className="text-gray-400" />}
      </IconBox>
      <span className="truncate">{record.platform?.name || 'No platform'}</span>
    </span>
  )
}

const MAX_VISIBLE_CHIPS = 2

/**
 * Renders compact "ownership chips" for a media item and all of its linked
 * copies — one LocationChip per physical member, one PlatformChip per
 * digital member. Beyond MAX_VISIBLE_CHIPS, the rest collapse into a "+N"
 * badge (hover for the full list).
 */
export default function OwnershipRow({ item, className }) {
  const members = [item, ...(item.linked_items || [])].filter(
    (m) => m.supertype === 'physical' || m.supertype === 'digital'
  )
  if (members.length === 0) return null

  const chips = members.map((m) =>
    m.supertype === 'physical'
      ? {
          key: `loc-${m.id}`,
          node: <LocationChip record={m} />,
          label: m.location_path || m.location_name || 'No location',
        }
      : {
          key: `plat-${m.id}`,
          node: <PlatformChip record={m} />,
          label: m.platform?.name || 'No platform',
        }
  )

  const visible = chips.slice(0, MAX_VISIBLE_CHIPS)
  const overflow = chips.slice(MAX_VISIBLE_CHIPS)

  return (
    <div className={clsx('flex items-center gap-1.5 flex-wrap', className)}>
      {visible.map((c) => (
        <span key={c.key}>{c.node}</span>
      ))}
      {overflow.length > 0 && (
        <span
          className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400"
          title={overflow.map((c) => c.label).join(', ')}
        >
          +{overflow.length}
        </span>
      )}
    </div>
  )
}
