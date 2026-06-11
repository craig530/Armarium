import { Tv } from 'lucide-react'
import clsx from 'clsx'
import LocationIcon from '../ui/LocationIcon'
import { platformLogoUrl } from '../../lib/platformLogos'

function IconBox({ children }) {
  return (
    <span className="shrink-0 h-5 w-5 rounded bg-white dark:bg-gray-900 flex items-center justify-center p-0.5">
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

/**
 * Renders the location-icon and/or platform-logo "ownership chips" for a
 * media item. For unified (linked) items, `item` and `item.linked_item` are
 * one physical and one digital record — exactly one chip is shown per side.
 */
export default function OwnershipRow({ item, className }) {
  const linked = item.linked_item
  const physical = item.supertype === 'physical' ? item : linked?.supertype === 'physical' ? linked : null
  const digital = item.supertype === 'digital' ? item : linked?.supertype === 'digital' ? linked : null

  if (!physical && !digital) return null

  return (
    <div className={clsx('flex items-center gap-1.5 flex-wrap', className)}>
      {physical && <LocationChip record={physical} />}
      {digital && <PlatformChip record={digital} />}
    </div>
  )
}
