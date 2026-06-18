import { MapPin, Tv, Tags, Cast, ListChecks } from 'lucide-react'

// Shared between the Profile page's Settings section (see Profile.jsx).
// Ownership has moved to the Admin panel.
export const MANAGE_LINKS = [
  { to: '/settings/locations', label: 'Locations', icon: MapPin },
  { to: '/settings/platforms', label: 'Platforms', icon: Tv },
  { to: '/settings/media-subtypes', label: 'Mediums', icon: Tags },
  { to: '/settings/lists', label: 'Lists', icon: ListChecks },
  { to: '/settings/plex', label: 'Plex Sync', icon: Cast },
]
