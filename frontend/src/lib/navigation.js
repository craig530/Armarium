import { MapPin, Tv, Tags, Cast } from 'lucide-react'

// Shared between the desktop Navbar's "Manage" dropdown and the Profile
// page's mobile equivalent (see Navbar.jsx and Profile.jsx).
export const MANAGE_LINKS = [
  { to: '/settings/locations', label: 'Locations', icon: MapPin },
  { to: '/settings/platforms', label: 'Platforms', icon: Tv },
  { to: '/settings/media-subtypes', label: 'Mediums', icon: Tags },
  { to: '/settings/plex', label: 'Plex Sync', icon: Cast },
]
