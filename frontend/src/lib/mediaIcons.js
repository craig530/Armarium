import { Disc, Disc3, Music, Clapperboard, Tv2, BookOpen, Image, Tablet, Headphones, Package, Cloud } from 'lucide-react'

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
}

// Per-category icon, used both as the fallback for getSubtypeIcon (a custom
// subtype with no specific NAME_ICONS entry) and directly wherever a
// category (rather than a subtype) needs an icon — nav links, the add-item
// type picker, cover-image placeholders, etc.
export const CATEGORY_ICONS = {
  music: Music,
  films_tv: Clapperboard,
  books: BookOpen,
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
