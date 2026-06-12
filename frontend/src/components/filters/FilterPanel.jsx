import { useLibraryStore } from '../../store'
import { CATEGORIES, SUPERTYPES } from '../../lib/categories'
import Button from '../ui/Button'
import SelectMenu from '../ui/SelectMenu'
import LocationPicker from '../locations/LocationPicker'

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date added' },
  { value: 'title', label: 'Title' },
  { value: 'year', label: 'Year' },
]

// Filter row shared by Library (one category, filters come from the global
// useLibraryStore) and the "All" Home view (showCategory, filters are local
// to the page and passed in as props).
export default function FilterPanel({
  locations = [],
  mediaSubtypes = [],
  platforms = [],
  category,
  showCategory = false,
  filters: filtersProp,
  setFilter: setFilterProp,
  resetFilters: resetFiltersProp,
}) {
  const libraryStore = useLibraryStore()
  const filters = filtersProp || libraryStore.filters
  const setFilter = setFilterProp || libraryStore.setFilter
  const resetFilters = resetFiltersProp || libraryStore.resetFilters

  const effectiveCategory = category || filters.category

  const supertypeFilteredSubtypes = mediaSubtypes
    .filter((s) => !filters.supertype || s.supertype === filters.supertype)

  // With a category fixed (Library, or "All" once a category is chosen),
  // group subtypes by Physical/Digital as before. Otherwise ("All" with no
  // category selected), group by category so the select covers everything.
  const subtypeGroups = effectiveCategory
    ? (() => {
        const categorySubtypes = supertypeFilteredSubtypes
          .filter((s) => s.category === effectiveCategory)
          .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
        return [
          { label: 'Physical', subtypes: categorySubtypes.filter((s) => s.supertype === 'physical') },
          { label: 'Digital', subtypes: categorySubtypes.filter((s) => s.supertype === 'digital') },
        ]
      })()
    : CATEGORIES.map((c) => ({
        label: c.label,
        subtypes: supertypeFilteredSubtypes
          .filter((s) => s.category === c.value)
          .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
      }))

  const handleCategoryChange = (value) => {
    setFilter('category', value)
    if (filters.media_subtype_id) setFilter('media_subtype_id', '')
  }

  const hasActiveFilters = !!(
    filters.q || filters.supertype || filters.media_subtype_id || filters.platform_id ||
    filters.genre || filters.year || filters.location_id || (showCategory && filters.category)
  )

  const categoryGroups = [{
    options: [
      { value: '', label: 'All categories' },
      ...CATEGORIES.map((c) => ({ value: c.value, label: c.label })),
    ],
  }]

  const supertypeGroups = [{
    options: [
      { value: '', label: 'Physical & digital' },
      ...SUPERTYPES.map((t) => ({ value: t.value, label: t.label })),
    ],
  }]

  const mediaSubtypeGroups = [
    { options: [{ value: '', label: 'All types' }] },
    ...subtypeGroups
      .filter((g) => g.subtypes.length > 0)
      .map((g) => ({ label: g.label, options: g.subtypes.map((s) => ({ value: String(s.id), label: s.name })) })),
  ]

  const platformGroups = [{
    options: [
      { value: '', label: 'All platforms' },
      ...platforms.map((p) => ({ value: String(p.id), label: p.name })),
    ],
  }]

  const sortGroups = [{ options: SORT_OPTIONS.map((s) => ({ value: s.value, label: s.label })) }]

  const orderGroups = [{
    options: [
      { value: 'desc', label: 'Newest' },
      { value: 'asc', label: 'Oldest' },
    ],
  }]

  return (
    <div className="flex flex-wrap gap-3 items-end">
      {showCategory && (
        <SelectMenu groups={categoryGroups} value={filters.category || ''} onChange={handleCategoryChange} className="w-40" />
      )}

      <SelectMenu groups={supertypeGroups} value={filters.supertype} onChange={(value) => setFilter('supertype', value)} className="w-36" />

      <SelectMenu groups={mediaSubtypeGroups} value={filters.media_subtype_id} onChange={(value) => setFilter('media_subtype_id', value)} className="w-40" />

      {platforms.length > 0 && (
        <SelectMenu groups={platformGroups} value={filters.platform_id} onChange={(value) => setFilter('platform_id', value)} className="w-40" />
      )}

      <LocationPicker
        locations={locations}
        value={filters.location_id}
        onChange={(value) => setFilter('location_id', value)}
        placeholder="All locations"
        className="w-48"
      />

      <SelectMenu groups={sortGroups} value={filters.sort} onChange={(value) => setFilter('sort', value)} className="w-40" />

      <SelectMenu groups={orderGroups} value={filters.order} onChange={(value) => setFilter('order', value)} className="w-28" />

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={resetFilters}>
          Clear filters
        </Button>
      )}
    </div>
  )
}
