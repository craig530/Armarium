import { Disc } from 'lucide-react'
import { OwnershipIcon } from '../ui/Badge'
import { OWNERSHIP_LABELS } from '../../lib/mediaIcons'

// Explains the small subtype/ownership icons shown on media cards and rows.
export default function IconLegend() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-gray-400">
      <span className="flex items-center gap-1.5">
        <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
          <Disc size={14} />
        </span>
        Format
      </span>
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
