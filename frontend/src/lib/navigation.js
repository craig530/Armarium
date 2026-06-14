import { MapPin, Tv, Tags, Cast } from 'lucide-react'

// Shared between the desktop Navbar's "Manage" dropdown and the Profile
// page's mobile equivalent (see Navbar.jsx and Profile.jsx).
export const MANAGE_LINKS = [
  { to: '/settings/locations', label: 'Manage Locations', icon: MapPin },
  { to: '/settings/platforms', label: 'Manage Platforms', icon: Tv },
  { to: '/settings/media-subtypes', label: 'Manage Media Types', icon: Tags },
  { to: '/settings/plex', label: 'Plex Sync', icon: Cast },
]
