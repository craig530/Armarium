import { Settings2, LogOut } from 'lucide-react'
import Button from '../ui/Button'
import LocationIcon from '../ui/LocationIcon'
import PlatformLogo from '../ui/PlatformLogo'
import { flattenLocations } from '../../lib/locations'

// Persistent strip shown above the scan/search step (and edition/form steps)
// while batch mode is active. Tapping the location/platform opens the
// change picker; "Exit batch" is always reachable from here.
export default function BatchStatusBar({ supertype, locationId, platformId, locations, platforms, onChangeLocation, onExit }) {
  const isPhysical = supertype === 'physical'
  const location = isPhysical ? flattenLocations(locations).find((l) => String(l.id) === String(locationId)) : null
  const platform = !isPhysical ? platforms.find((p) => String(p.id) === String(platformId)) : null

  return (
    <div className="flex items-center justify-between gap-2 rounded-xl border border-brand-200 dark:border-brand-800 bg-brand-50 dark:bg-brand-950/40 px-3 py-2">
      <button
        type="button"
        onClick={onChangeLocation}
        className="flex flex-1 items-center gap-2 min-w-0 text-left"
      >
        {isPhysical ? (
          <LocationIcon location={location} size={16} className="shrink-0 text-brand-600 dark:text-brand-400" />
        ) : (
          <PlatformLogo platform={platform} className="h-6 w-6 shrink-0" />
        )}
        <span className="truncate text-sm font-medium text-brand-900 dark:text-brand-100">
          {isPhysical ? (location?.path || 'No location') : (platform?.name || 'No platform')}
        </span>
        <Settings2 size={13} className="shrink-0 text-brand-500" />
      </button>
      <Button type="button" size="sm" variant="outline" onClick={onExit} className="shrink-0">
        <LogOut size={14} />
        Exit batch
      </Button>
    </div>
  )
}
