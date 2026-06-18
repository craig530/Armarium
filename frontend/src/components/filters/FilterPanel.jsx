import { useLibraryStore, useReferenceDataStore } from '../../store'
import { CATEGORIES, SUPERTYPES } from '../../lib/categories'
import { flattenLocations, reachableLocationIds } from '../../lib/locations'
import Button from '../ui/Button'
import SelectMenu from '../ui/SelectMenu'
import LocationPicker from '../locations/LocationPicker'
import PlatformLogo from '../ui/PlatformLogo'

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
  lists = [],
  users = [],
  facetLocationIds = null,
  facetPlatformIds = null,
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

  const appConfig = useReferenceDataStore((s) => s.appConfig)
  const disabledCategories = appConfig?.disabled_categories ?? []
  const visibleCategoryList = CATEGORIES.filter((c) => !disabledCategories.includes(c.value))

  const effectiveCategory = category || filters.category

  // Limit locations to those reachable given facets (used IDs + ancestors).
  // When facets aren't provided, show everything.
  const visibleLocations = facetLocationIds
    ? (() => {
        const flat = flattenLocations(locations)
        const reachable = reachableLocationIds(flat, facetLocationIds)
        // Rebuild nested tree from the reachable flat set — LocationPicker
        // accepts the original nested structure, so filter top-level and
        // children recursively.
        function filterTree(nodes) {
          return nodes
            .map((n) => ({ ...n, children: filterTree(n.children || []) }))
            .filter((n) => reachable.has(n.id) || n.children.length > 0)
        }
        return filterTree(locations)
      })()
    : locations

  // Limit platforms to those with items in current context.
  const visiblePlatforms = facetPlatformIds
    ? platforms.filter((p) => facetPlatformIds.has(p.id))
    : platforms

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
    : visibleCategoryList.map((c) => ({
        label: c.label,
        subtypes: supertypeFilteredSubtypes
          .filter((s) => s.category === c.value)
          .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
      }))

  const handleCategoryChange = (value) => {
    setFilter('category', value)
    if (filters.media_subtype_id) setFilter('media_subtype_id', '')
    if (filters.list_id) setFilter('list_id', '')
  }

  const hasActiveFilters = !!(
    filters.q || filters.supertype || filters.media_subtype_id || filters.platform_id ||
    filters.genre || filters.year || filters.location_id || filters.list_id || filters.owner_id ||
    filters.rating || (showCategory && filters.category)
  )

  const categoryGroups = [{
    options: [
      { value: '', label: 'All categories' },
      ...visibleCategoryList.map((c) => ({ value: c.value, label: c.label })),
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
      ...visiblePlatforms.map((p) => ({ value: String(p.id), label: p.name, platform: p })),
    ],
  }]

  const listLabel = (l) =>
    l.owner_username && l.owner_username !== 'shared'
      ? `${l.name} (${l.owner_username})`
      : l.name

  const listGroups = effectiveCategory
    ? [{
        options: [
          { value: '', label: 'All lists' },
          ...lists
            .filter((l) => l.category === effectiveCategory)
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((l) => ({ value: String(l.id), label: listLabel(l) })),
        ],
      }]
    : [
        { options: [{ value: '', label: 'All lists' }] },
        ...visibleCategoryList.map((c) => ({
          label: c.label,
          options: lists
            .filter((l) => l.category === c.value)
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((l) => ({ value: String(l.id), label: listLabel(l) })),
        })).filter((g) => g.options.length > 0),
      ]

  const ownerGroups = [{
    options: [
      { value: '', label: 'All owners' },
      ...users.map((u) => ({ value: String(u.id), label: u.username })),
    ],
  }]

  const ratingGroups = [{
    options: [
      { value: '', label: 'Any rating' },
      { value: 'unrated', label: 'No rating' },
      { value: '3', label: '3 stars or more' },
      { value: '4', label: '4 stars or more' },
      { value: '5', label: '5 stars' },
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

      {visiblePlatforms.length > 0 && (
        <SelectMenu
          groups={platformGroups}
          value={filters.platform_id}
          onChange={(value) => setFilter('platform_id', value)}
          renderIcon={(opt) => opt.platform && <PlatformLogo platform={opt.platform} className="h-5 w-5" />}
          className="w-40"
        />
      )}

      {visibleLocations.length > 0 && (
        <LocationPicker
          locations={visibleLocations}
          value={filters.location_id}
          onChange={(value) => setFilter('location_id', value)}
          placeholder="All locations"
          className="w-48"
        />
      )}

      {lists.length > 0 && (
        <SelectMenu groups={listGroups} value={filters.list_id} onChange={(value) => setFilter('list_id', value)} className="w-40" />
      )}

      {users.length > 0 && (
        <SelectMenu groups={ownerGroups} value={filters.owner_id || ''} onChange={(value) => setFilter('owner_id', value)} className="w-36" />
      )}

      <SelectMenu groups={ratingGroups} value={filters.rating || ''} onChange={(value) => setFilter('rating', value)} className="w-40" />

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
