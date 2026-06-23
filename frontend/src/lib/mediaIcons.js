import { Disc, Disc3, Music, Clapperboard, Tv2, BookOpen, Image, Tablet, Headphones, Package, Cloud, Gamepad2, MemoryStick, Library, Boxes } from 'lucide-react'

// Icon lookup by media subtype name (case-insensitive), for the default
// seeded subtypes. Custom subtypes fall back to a category-level icon below.
const NAME_ICONS = {
  cd: Disc,
  dvd: Disc,
  'blu-ray': Disc3,
  music: Music,
  film: Clapperboard,
  'tv series': Tv2,
  book: BookOpen,
  'graphic novel': Image,
  ebook: Tablet,
  audiobook: Headphones,
  // Games
  disc: Disc,
  cartridge: MemoryStick,
  game: Gamepad2,
}

// Per-category icon, used both as the fallback for getSubtypeIcon (a custom
// subtype with no specific NAME_ICONS entry) and directly wherever a
// category (rather than a subtype) needs an icon — nav links, the add-item
// type picker, cover-image placeholders, etc.
export const CATEGORY_ICONS = {
  music: Music,
  films_tv: Clapperboard,
  books: BookOpen,
  games: Gamepad2,
}

// Empty-collection illustrations — a more characterful stand-in for the
// generic "no items" box, themed per category. "all" covers the Home page's
// combined empty state, which spans every category at once.
export const EMPTY_STATE_ICONS = {
  music: Disc3,
  films_tv: Clapperboard,
  books: Library,
  games: Gamepad2,
  all: Boxes,
}

export function getSubtypeIcon(subtype) {
  if (!subtype) return null
  const byName = NAME_ICONS[subtype.name?.toLowerCase().trim()]
  return byName || CATEGORY_ICONS[subtype.category] || null
}

export const OWNERSHIP_ICONS = {
  physical: Package,
  digital: Cloud,
}

export const OWNERSHIP_LABELS = {
  physical: 'Physical',
  digital: 'Digital',
  both: 'Both',
}
