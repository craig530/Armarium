import { useLibraryStore } from '../../store'
import { CATEGORIES, SUPERTYPES } from '../../lib/categories'
import { Select } from '../ui/Input'
import Button from '../ui/Button'
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

  return (
    <div className="flex flex-wrap gap-3 items-end">
      {showCategory && (
        <Select
          value={filters.category || ''}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="w-40"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </Select>
      )}

      <Select
        value={filters.supertype}
        onChange={(e) => setFilter('supertype', e.target.value)}
        className="w-36"
      >
        <option value="">Physical & digital</option>
        {SUPERTYPES.map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </Select>

      <Select
        value={filters.media_subtype_id}
        onChange={(e) => setFilter('media_subtype_id', e.target.value)}
        className="w-40"
      >
        <option value="">All types</option>
        {subtypeGroups.filter((g) => g.subtypes.length > 0).map((g) => (
          <optgroup key={g.label} label={g.label}>
            {g.subtypes.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </optgroup>
        ))}
      </Select>

      {platforms.length > 0 && (
        <Select
          value={filters.platform_id}
          onChange={(e) => setFilter('platform_id', e.target.value)}
          className="w-40"
        >
          <option value="">All platforms</option>
          {platforms.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </Select>
      )}

      <LocationPicker
        locations={locations}
        value={filters.location_id}
        onChange={(value) => setFilter('location_id', value)}
        placeholder="All locations"
        className="w-48"
      />

      <Select
        value={filters.sort}
        onChange={(e) => setFilter('sort', e.target.value)}
        className="w-40"
      >
        {SORT_OPTIONS.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </Select>

      <Select
        value={filters.order}
        onChange={(e) => setFilter('order', e.target.value)}
        className="w-28"
      >
        <option value="desc">Newest</option>
        <option value="asc">Oldest</option>
      </Select>

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={resetFilters}>
          Clear filters
        </Button>
      )}
    </div>
  )
}
