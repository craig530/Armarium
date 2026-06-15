import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import clsx from 'clsx'
import { Plus, SlidersHorizontal } from 'lucide-react'
import { mediaApi } from '../api/media'
import { useReferenceDataStore } from '../store'
import { CATEGORIES } from '../lib/categories'
import { dedupeLinkedItems } from '../lib/media'
import MediaRow from '../components/media/MediaRow'
import MediaCard from '../components/media/MediaCard'
import IconLegend from '../components/media/IconLegend'
import FilterPanel from '../components/filters/FilterPanel'
import SearchInput from '../components/ui/SearchInput'
import Button from '../components/ui/Button'
import { SkeletonCard } from '../components/ui/Skeleton'
import toast from 'react-hot-toast'

const ROW_PER_PAGE = 20
const SKELETON_COUNT = 12

const DEFAULT_FILTERS = {
  q: '',
  category: '',
  supertype: '',
  media_subtype_id: '',
  platform_id: '',
  location_id: '',
  list_id: '',
  sort: 'created_at',
  order: 'desc',
}

export default function Home() {
  const navigate = useNavigate()
  const { locations, mediaSubtypes, platforms, lists, ensureLoaded } = useReferenceDataStore()

  // Unfiltered "browse" rows
  const [recent, setRecent] = useState(null)
  const [byCategory, setByCategory] = useState({})
  const [browseLoading, setBrowseLoading] = useState(true)

  // Local search/filter state (kept separate from useLibraryStore so it
  // doesn't cross-contaminate Library's per-category filters)
  const [filters, setFiltersState] = useState(DEFAULT_FILTERS)
  const [searchInput, setSearchInput] = useState('')
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const abortRef = useRef(null)

  const setFilter = (key, value) => setFiltersState((f) => ({ ...f, [key]: value }))
  const resetFilters = () => { setFiltersState(DEFAULT_FILTERS); setSearchInput('') }

  const hasActiveFilters = !!(
    filters.q || filters.category || filters.supertype ||
    filters.media_subtype_id || filters.platform_id || filters.location_id || filters.list_id
  )

  useEffect(() => { ensureLoaded() }, [ensureLoaded])

  useEffect(() => {
    if (hasActiveFilters) return
    let cancelled = false
    setBrowseLoading(true)

    Promise.all([
      mediaApi.list({ sort: 'created_at', order: 'desc', per_page: ROW_PER_PAGE }),
      ...CATEGORIES.map((c) =>
        mediaApi.list({ category: c.value, sort: 'created_at', order: 'desc', per_page: ROW_PER_PAGE })
      ),
    ])
      .then(([recentResult, ...categoryResults]) => {
        if (cancelled) return
        setRecent(recentResult)
        const map = {}
        CATEGORIES.forEach((c, i) => { map[c.value] = categoryResults[i] })
        setByCategory(map)
      })
      .catch((err) => toast.error(err.message))
      .finally(() => { if (!cancelled) setBrowseLoading(false) })

    return () => { cancelled = true }
  }, [hasActiveFilters])

  const load = useCallback(async (p = 1) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    try {
      const params = {
        page: p,
        per_page: 24,
        sort: filters.sort,
        order: filters.order,
        ...(filters.q && { q: filters.q }),
        ...(filters.category && { category: filters.category }),
        ...(filters.supertype && { supertype: filters.supertype }),
        ...(filters.media_subtype_id && { media_subtype_id: filters.media_subtype_id }),
        ...(filters.platform_id && { platform_id: filters.platform_id }),
        ...(filters.location_id && { location_id: filters.location_id }),
        ...(filters.list_id && { list_id: filters.list_id }),
      }
      const result = await mediaApi.list(params, { signal: controller.signal })
      setData(result)
      setPage(p)
      setLoading(false)
    } catch (err) {
      if (axios.isCancel(err)) return
      toast.error(err.message)
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    if (hasActiveFilters) load(1)
  }, [load, hasActiveFilters])

  // Debounce the search box, same as Library.
  useEffect(() => {
    const handle = setTimeout(() => {
      if (searchInput !== filters.q) setFilter('q', searchInput)
    }, 300)
    return () => clearTimeout(handle)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput])

  const isEmpty = !browseLoading && recent && recent.total === 0

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">All</h1>

      {/* Search + filters toggle */}
      <div className="flex gap-3">
        <SearchInput
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search titles, authors, directors… (press /)"
          className="flex-1"
        />

        {/* Filters toggle — filters are always visible from sm: up, so this
            button (and its expanded panel below) only render on mobile. */}
        <Button
          variant="outline"
          onClick={() => setFiltersOpen((o) => !o)}
          className="sm:hidden relative justify-center"
        >
          <SlidersHorizontal size={16} />
          Filters
          {hasActiveFilters && (
            <span className="absolute top-1.5 right-2.5 h-2 w-2 rounded-full bg-brand-600" />
          )}
        </Button>
      </div>

      {/* Filters — collapsed by default on mobile (toggled above), always visible from sm: up */}
      <div className={clsx(!filtersOpen && 'hidden sm:block')}>
        <FilterPanel
          showCategory
          locations={locations}
          mediaSubtypes={mediaSubtypes}
          platforms={platforms}
          lists={lists}
          filters={filters}
          setFilter={setFilter}
          resetFilters={resetFilters}
        />
      </div>

      {!hasActiveFilters && isEmpty && (
        <div className="text-center py-24 space-y-4">
          <div className="text-6xl">📦</div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Your collection is empty</h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
            Start cataloguing your music, films, TV and books — physical or digital.
          </p>
          <Button onClick={() => navigate('/add')} className="mx-auto">
            <Plus size={16} /> Add your first item
          </Button>
        </div>
      )}

      {!hasActiveFilters && !isEmpty && (
        <>
          <MediaRow
            title="Recently Added"
            items={recent ? dedupeLinkedItems(recent.items) : []}
            loading={browseLoading}
          />
          {CATEGORIES.map((c) => (
            <MediaRow
              key={c.value}
              title={c.label}
              items={byCategory[c.value] ? dedupeLinkedItems(byCategory[c.value].items) : []}
              seeAllHref={`/library/${c.slug}`}
              loading={browseLoading}
            />
          ))}

          {!browseLoading && <IconLegend items={recent ? dedupeLinkedItems(recent.items) : []} />}
        </>
      )}

      {hasActiveFilters && (
        <>
          {!loading && data?.total === 0 && (
            <div className="text-center py-16 space-y-3">
              <div className="text-4xl">🔍</div>
              <p className="text-gray-600 dark:text-gray-400 font-medium">No results match your search</p>
              <p className="text-sm text-gray-400">Try different keywords or clear the filters</p>
            </div>
          )}

          {loading && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
              {Array.from({ length: SKELETON_COUNT }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          )}

          {!loading && data && data.items.length > 0 && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                {dedupeLinkedItems(data.items).map((item) => <MediaCard key={item.id} item={item} />)}
              </div>

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

              <IconLegend items={dedupeLinkedItems(data.items)} />

              <p className="text-xs text-center text-gray-400">
                {data.total} item{data.total !== 1 ? 's' : ''}
              </p>
            </>
          )}
        </>
      )}
    </div>
  )
}
