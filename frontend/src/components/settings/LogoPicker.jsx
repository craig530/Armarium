import { useRef } from 'react'
import { Upload, Tv } from 'lucide-react'
import clsx from 'clsx'
import { PLATFORM_LOGOS } from '../../lib/platformLogos'

const SWATCH_CLASSES = 'aspect-square rounded-lg border flex items-center justify-center p-1.5 bg-white dark:bg-gray-900 transition-colors'
const SWATCH_ACTIVE = 'border-brand-500 ring-1 ring-brand-500'
const SWATCH_INACTIVE = 'border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-700'

const BUILTIN_LOGOS = Object.entries(PLATFORM_LOGOS).filter(([, p]) => p.logoUrl)

/**
 * Grid picker for built-in platform logos (from `simple-icons`), plus an
 * optional custom upload. `logoUrl` (custom upload) takes priority for
 * display over `logoKey`.
 */
export default function LogoPicker({ logoKey, logoUrl, onSelect, onUpload }) {
  const fileRef = useRef(null)

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block">Logo</label>
      <div className="grid grid-cols-6 sm:grid-cols-8 gap-1.5">
        <button
          type="button"
          onClick={() => onSelect(null)}
          title="No logo"
          className={clsx(SWATCH_CLASSES, !logoKey && !logoUrl ? SWATCH_ACTIVE : SWATCH_INACTIVE)}
        >
          <Tv size={16} className="text-gray-400" />
        </button>
        {BUILTIN_LOGOS.map(([key, { label, logoUrl: builtinUrl }]) => (
          <button
            key={key}
            type="button"
            onClick={() => onSelect(key)}
            title={label}
            className={clsx(SWATCH_CLASSES, !logoUrl && logoKey === key ? SWATCH_ACTIVE : SWATCH_INACTIVE)}
          >
            <img src={builtinUrl} alt={label} className="h-full w-full object-contain" />
          </button>
        ))}
        {onUpload && (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            title="Upload custom logo"
            className={clsx(SWATCH_CLASSES, logoUrl ? SWATCH_ACTIVE : SWATCH_INACTIVE)}
          >
            {logoUrl ? <img src={logoUrl} alt="" className="h-full w-full object-contain" /> : <Upload size={16} className="text-gray-400" />}
          </button>
        )}
      </div>
      {onUpload && (
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
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
