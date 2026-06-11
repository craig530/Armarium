// Top-level library groupings. `slug` is used in routes (/library/:slug),
// `value` is the MediaCategory enum value used by the API.
export const CATEGORIES = [
  { slug: 'music', value: 'music', label: 'Music' },
  { slug: 'films-tv', value: 'films_tv', label: 'Films & TV' },
  { slug: 'books', value: 'books', label: 'Books' },
]

export const DEFAULT_CATEGORY_SLUG = CATEGORIES[0].slug

export function categoryFromSlug(slug) {
  return CATEGORIES.find((c) => c.slug === slug)?.value ?? null
}

export function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value
}

export const SUPERTYPES = [
  { value: 'physical', label: 'Physical' },
  { value: 'digital', label: 'Digital' },
]
