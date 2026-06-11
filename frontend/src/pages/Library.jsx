import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams, Navigate } from 'react-router-dom'
import { LayoutGrid, List, Plus, Search } from 'lucide-react'
import { mediaApi } from '../api/media'
import { locationsApi } from '../api/locations'
import { useLibraryStore } from '../store'
import { CATEGORIES, DEFAULT_CATEGORY_SLUG, categoryFromSlug, categoryLabel } from '../lib/categories'
import MediaCard from '../components/media/MediaCard'
import MediaListRow from '../components/media/MediaListRow'
import FilterPanel from '../components/filters/FilterPanel'
import Button from '../components/ui/Button'
import { SkeletonCard, SkeletonListRow } from '../components/ui/Skeleton'
import toast from 'react-hot-toast'

const SKELETON_COUNT = 12

const EMPTY_COPY = {
  music: 'Start cataloguing your CDs, vinyl and digital or streaming music. Scan a barcode or search by title to get started.',
  films_tv: 'Start cataloguing your DVDs, Blu-rays, and digital or streaming films & TV. Scan a barcode or search by title to get started.',
  books: 'Start cataloguing your books and graphic novels. Scan a barcode or search by title to get started.',
}

export default function Library() {
  const navigate = useNavigate()
  const { category: categorySlug } = useParams()
  const category = categoryFromSlug(categorySlug)
  const { viewMode, setViewMode, filters, setFilter } = useLibraryStore()

  const [data, setData] = useState(null)
  const [stats, setStats] = useState(null)
  const [locations, setLocations] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (p = 1) => {
    if (!category) return
    setLoading(true)
    try {
      const params = {
        page: p,
        per_page: 24,
        category,
        sort: filters.sort,
        order: filters.order,
        ...(filters.q && { q: filters.q }),
        ...(filters.supertype && { supertype: filters.supertype }),
        ...(filters.media_subtype_id && { media_subtype_id: filters.media_subtype_id }),
        ...(filters.platform_id && { platform_id: filters.platform_id }),
        ...(filters.genre && { genre: filters.genre }),
        ...(filters.year && { year: filters.year }),
        ...(filters.location_id && { location_id: filters.location_id }),
      }
      const result = await mediaApi.list(params)
      setData(result)
      setPage(p)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }, [category, filters])

  useEffect(() => { load(1) }, [load])

  useEffect(() => {
    mediaApi.stats().then(setStats).catch(() => {})
    locationsApi.list().then(setLocations).catch(() => {})
  }, [])

  if (!category) {
    return <Navigate to={`/library/${DEFAULT_CATEGORY_SLUG}`} replace />
  }

  const handleDeleted = (id) => {
    setData((d) => d ? { ...d, items: d.items.filter((i) => i.id !== id), total: d.total - 1 } : d)
  }

  const hasActiveFilters = Object.entries(filters).some(([k, v]) => {
    if (k === 'sort' || k === 'order') return false
    return !!v
  })
  const isEmpty = !loading && data && data.total === 0 && !hasActiveFilters

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{categoryLabel(category)}</h1>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total', count: stats.total, color: 'text-gray-900 dark:text-white' },
            ...CATEGORIES.map((c) => ({
              label: c.label,
              count: stats.by_category?.[c.value] || 0,
              color: c.value === category ? 'text-brand-600 dark:text-brand-400' : 'text-gray-700 dark:text-gray-300',
            })),
          ].map(({ label, count, color }) => (
            <div key={label} className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-3">
              <p className={`text-2xl font-bold ${color}`}>{count}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Search + view controls */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            data-search
            value={filters.q}
            onChange={(e) => setFilter('q', e.target.value)}
            placeholder="Search titles, authors, directors… (press /)"
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {[
            { mode: 'grid', Icon: LayoutGrid },
            { mode: 'list', Icon: List },
          ].map(({ mode, Icon }) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              title={`${mode} view (${mode[0]})`}
              className={`px-3 py-2 transition-colors ${
                viewMode === mode
                  ? 'bg-brand-600 text-white'
                  : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
            >
              <Icon size={16} />
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <FilterPanel locations={locations} category={category} />

      {/* Empty library */}
      {isEmpty && (
        <div className="text-center py-24 space-y-4">
          <div className="text-6xl">📦</div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">No {categoryLabel(category).toLowerCase()} yet</h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
            {EMPTY_COPY[category]}
          </p>
          <Button onClick={() => navigate('/add')} className="mx-auto">
            <Plus size={16} /> Add your first item
          </Button>
        </div>
      )}

      {/* No results from search/filter */}
      {!loading && !isEmpty && data?.total === 0 && (
        <div className="text-center py-16 space-y-3">
          <div className="text-4xl">🔍</div>
          <p className="text-gray-600 dark:text-gray-400 font-medium">No results match your search</p>
          <p className="text-sm text-gray-400">Try different keywords or clear the filters</p>
        </div>
      )}

      {/* Skeleton grid/list while loading */}
      {loading && (
        viewMode === 'grid' ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {Array.from({ length: SKELETON_COUNT }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : (
          <div className="space-y-1">
            {Array.from({ length: 8 }).map((_, i) => <SkeletonListRow key={i} />)}
          </div>
        )
      )}

      {/* Results */}
      {!loading && data && data.items.length > 0 && (
        <>
          {viewMode === 'grid' ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
              {data.items.map((item) => <MediaCard key={item.id} item={item} />)}
            </div>
          ) : (
            <div className="space-y-1">
              {data.items.map((item) => (
                <MediaListRow key={item.id} item={item} onDeleted={handleDeleted} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => load(page - 1)}>
                Previous
              </Button>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {page} / {data.pages}
              </span>
              <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => load(page + 1)}>
                Next
              </Button>
            </div>
          )}

          <p className="text-xs text-center text-gray-400">
            {data.total} item{data.total !== 1 ? 's' : ''}
          </p>
        </>
      )}
    </div>
  )
}
