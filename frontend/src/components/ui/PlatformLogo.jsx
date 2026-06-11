import { Tv } from 'lucide-react'
import { platformLogoUrl } from '../../lib/platformLogos'

export default function PlatformLogo({ platform, size = 16, className = 'h-8 w-8' }) {
  const url = platformLogoUrl(platform)
  return (
    <div className={`shrink-0 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden p-1 ${className}`}>
      {url ? (
        <img src={url} alt="" className="h-full w-full object-contain" />
      ) : (
        <Tv size={size} className="text-gray-400" />
      )}
    </div>
  )
}
