// Built-in location icon set: a curated subset of lucide-react, used by the
// location icon picker and rendered wherever a location is shown. Lucide
// icons use `currentColor`, so dark mode "inversion" is automatic via the
// surrounding text-colour utility classes — no separate dark-mode assets
// needed (unlike platform logos, which keep their brand colour).
import {
  Library,
  Inbox,
  Box,
  DoorClosed,
  Package,
  Shirt,
  LampDesk,
  Building2,
  Warehouse,
  BedDouble,
  Sofa,
  Briefcase,
  UtensilsCrossed,
  Utensils,
  Building,
  Tv,
  Tv2,
  Container,
  Folder,
  Archive,
  MapPin,
} from 'lucide-react'

export const LOCATION_ICONS = {
  bookshelf: { label: 'Bookshelf', icon: Library },
  drawer: { label: 'Drawer', icon: Inbox },
  box: { label: 'Box', icon: Box },
  cabinet: { label: 'Cabinet', icon: DoorClosed },
  shelf: { label: 'Shelf', icon: Package },
  wardrobe: { label: 'Wardrobe', icon: Shirt },
  desk: { label: 'Desk', icon: LampDesk },
  loft: { label: 'Loft', icon: Building2 },
  garage: { label: 'Garage', icon: Warehouse },
  bedroom: { label: 'Bedroom', icon: BedDouble },
  living_room: { label: 'Living Room', icon: Sofa },
  office: { label: 'Office', icon: Briefcase },
  kitchen: { label: 'Kitchen', icon: UtensilsCrossed },
  dining_room: { label: 'Dining Room', icon: Utensils },
  basement: { label: 'Basement', icon: Building },
  tv_unit: { label: 'TV Unit', icon: Tv },
  media_cabinet: { label: 'Media Cabinet', icon: Tv2 },
  storage_unit: { label: 'Storage Unit', icon: Container },
  folder: { label: 'Folder', icon: Folder },
  archive: { label: 'Archive', icon: Archive },
}

// Fallback icon for locations with no icon_key/icon_url set.
export const DEFAULT_LOCATION_ICON = MapPin
