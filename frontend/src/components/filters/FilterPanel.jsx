import { useLibraryStore } from '../../store'
import { SUPERTYPES } from '../../lib/categories'
import { Select } from '../ui/Input'
import Button from '../ui/Button'

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date added' },
  { value: 'title', label: 'Title' },
  { value: 'year', label: 'Year' },
]

export default function FilterPanel({ locations = [] }) {
  const { filters, setFilter, resetFilters } = useLibraryStore()

  const flatLocations = []
  const flatten = (locs, depth = 0) => {
    for (const loc of locs) {
      flatLocations.push({ ...loc, depth })
      if (loc.children?.length) flatten(loc.children, depth + 1)
    }
  }
  flatten(locations)

  const hasActiveFilters = filters.q || filters.supertype || filters.media_subtype_id || filters.platform_id || filters.genre || filters.year || filters.location_id

  return (
    <div className="flex flex-wrap gap-3 items-end">
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
        value={filters.location_id}
        onChange={(e) => setFilter('location_id', e.target.value)}
        className="w-48"
      >
        <option value="">All locations</option>
        {flatLocations.map((loc) => (
          <option key={loc.id} value={loc.id}>
            {'  '.repeat(loc.depth)}{loc.name}
          </option>
        ))}
      </Select>

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
