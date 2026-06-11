import { useRef } from 'react'
import { Upload, Image as ImageIcon } from 'lucide-react'
import clsx from 'clsx'
import { LOCATION_ICONS, DEFAULT_LOCATION_ICON } from '../../lib/locationIcons'

const SWATCH_CLASSES = 'aspect-square rounded-lg border flex items-center justify-center transition-colors'
const SWATCH_ACTIVE = 'border-brand-500 bg-brand-50 dark:bg-brand-950 text-brand-600 dark:text-brand-400'
const SWATCH_INACTIVE = 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-brand-300 dark:hover:border-brand-700'

/**
 * Grid picker for built-in location icons, plus an optional custom upload.
 * `iconUrl` (if set) takes priority for display but a custom upload doesn't
 * clear `iconKey` server-side until a built-in icon is explicitly chosen.
 */
export default function IconPicker({ iconKey, iconUrl, onSelect, onUpload }) {
  const fileRef = useRef(null)

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block">Icon</label>
      <div className="grid grid-cols-8 sm:grid-cols-10 gap-1.5">
        <button
          type="button"
          onClick={() => onSelect(null)}
          title="No icon"
          className={clsx(SWATCH_CLASSES, !iconKey && !iconUrl ? SWATCH_ACTIVE : SWATCH_INACTIVE)}
        >
          <DEFAULT_LOCATION_ICON size={16} />
        </button>
        {Object.entries(LOCATION_ICONS).map(([key, { label, icon: Icon }]) => (
          <button
            key={key}
            type="button"
            onClick={() => onSelect(key)}
            title={label}
            className={clsx(SWATCH_CLASSES, !iconUrl && iconKey === key ? SWATCH_ACTIVE : SWATCH_INACTIVE)}
          >
            <Icon size={16} />
          </button>
        ))}
        {onUpload && (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            title="Upload custom icon"
            className={clsx(SWATCH_CLASSES, iconUrl ? SWATCH_ACTIVE : SWATCH_INACTIVE)}
          >
            {iconUrl ? <ImageIcon size={16} /> : <Upload size={16} />}
          </button>
        )}
      </div>
      {onUpload && (
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) onUpload(file)
            e.target.value = ''
          }}
        />
      )}
    </div>
  )
}
