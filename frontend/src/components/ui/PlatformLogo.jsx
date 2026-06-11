import { Tv } from 'lucide-react'
import { platformLogoUrl } from '../../lib/platformLogos'

// Deterministic accent colour for the letter-mark fallback, so the same
// platform name always renders with the same badge colour.
const ACCENT_CLASSES = [
  'bg-rose-500', 'bg-amber-500', 'bg-emerald-500', 'bg-sky-500',
  'bg-violet-500', 'bg-fuchsia-500', 'bg-orange-500', 'bg-teal-500',
]

function accentFor(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0
  return ACCENT_CLASSES[Math.abs(hash) % ACCENT_CLASSES.length]
}

function initialsFor(name) {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return '?'
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

// Resolves to, in order: a bundled brand SVG, a deterministic letter-mark
// badge for any named platform with no matching logo, or a generic icon.
export default function PlatformLogo({ platform, size = 16, className = 'h-8 w-8' }) {
  const url = platformLogoUrl(platform)

  if (url) {
    return (
      <div className={`shrink-0 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden p-1 ${className}`}>
        <img src={url} alt="" className="h-full w-full object-contain" />
      </div>
    )
  }

  if (platform?.name) {
    return (
      <div
        className={`shrink-0 rounded-lg flex items-center justify-center overflow-hidden font-semibold text-white ${accentFor(platform.name)} ${className}`}
      >
        <span style={{ fontSize: size * 0.6 }}>{initialsFor(platform.name)}</span>
      </div>
    )
  }

  return (
    <div className={`shrink-0 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden p-1 ${className}`}>
      <Tv size={size} className="text-gray-400" />
    </div>
  )
}
