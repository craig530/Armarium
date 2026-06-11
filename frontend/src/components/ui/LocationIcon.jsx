import { LOCATION_ICONS, DEFAULT_LOCATION_ICON } from '../../lib/locationIcons'

export default function LocationIcon({ location, size = 16, className = '' }) {
  if (location?.icon_url) {
    return (
      <img
        src={location.icon_url}
        alt=""
        className={`object-contain ${className}`}
        style={{ width: size, height: size }}
      />
    )
  }
  const Icon = LOCATION_ICONS[location?.icon_key]?.icon || DEFAULT_LOCATION_ICON
  return <Icon size={size} className={className} />
}
