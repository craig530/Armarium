import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { ChevronRight } from 'lucide-react'
import TypeStep from './TypeStep'
import LocationOrPlatformStep from './LocationOrPlatformStep'
import BatchModeStep from './BatchModeStep'
import BatchStatusBar from './BatchStatusBar'
import ChangeLocationModal from './ChangeLocationModal'
import EditItemModal from './EditItemModal'
import ItemListPanel from './ItemListPanel'
import ScanOrSearch from './ScanOrSearch'
import DigitalSearch from './DigitalSearch'
import EditionSelector from './EditionSelector'
import MetadataForm from './MetadataForm'
import LoadingSpinner from '../ui/LoadingSpinner'
import Button from '../ui/Button'
import { lookupApi } from '../../api/lookup'
import { mediaApi } from '../../api/media'
import { useReferenceDataStore } from '../../store'
import { CATEGORIES } from '../../lib/categories'

const SESSION_KEY = 'armarium-batch-session'

// Restores an in-progress batch session (e.g. after iOS Safari reclaims a
// backgrounded tab with an active camera). Only ever returns a session with
// batchMode on — a stale non-batch entry is just ignored.
function loadBatchSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    return data?.batchMode ? data : null
  } catch {
    return null
  }
}

// Each step is only ever pushed onto the stack when it's actually shown, so
// `back()` (pop) always returns to wherever the user really came from —
// e.g. a single-result search skips `edition` entirely, so going back from
// `form` returns straight to `search`/`digitalSearch`.
//
// type -> location | platform -> batchMode -> search | digitalSearch -> [edition] -> form
const STEP_GROUPS = {
  type: 0,
  location: 1,
  platform: 1,
  batchMode: 1,
  search: 2,
  digitalSearch: 2,
  edition: 2,
  form: 3,
}

export default function AddFlow({ onSaved }) {
  const navigate = useNavigate()
  const location = useLocation()
  const restored = loadBatchSession()

  const [stepStack, setStepStack] = useState(() =>
    restored ? [restored.supertype === 'physical' ? 'search' : 'digitalSearch'] : ['type']
  )
  // Captures the step this AddFlow instance started on, so the popstate
  // handler below has something to restore to once the user has backed out
  // of every step *it* pushed.
  const initialStackRef = useRef(stepStack)
  const lastSyncedKeyRef = useRef(location.key)
  const [category, setCategory] = useState(restored?.category ?? null)
  const [supertype, setSupertype] = useState(restored?.supertype ?? null)
  const [locationId, setLocationId] = useState(restored?.locationId ?? '')
  const [platformId, setPlatformId] = useState(restored?.platformId ?? '')
  const [batchMode, setBatchMode] = useState(restored?.batchMode ?? false)
  const [sessionItems, setSessionItems] = useState(restored?.sessionItems ?? [])
  const [recentItems, setRecentItems] = useState([])
  const [editingItem, setEditingItem] = useState(null)
  const [changingLocation, setChangingLocation] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)
  const [enriching, setEnriching] = useState(false)
  // Lifted out of ScanOrSearch/DigitalSearch so the search term and Film/TV
  // toggle survive a `back()` from edition/form back to the search step
  // (those components would otherwise remount with empty state).
  const [searchQuery, setSearchQuery] = useState('')
  const [mediaKind, setMediaKind] = useState('movie')

  const { locations, platforms, ensureLoaded } = useReferenceDataStore()
  useEffect(() => { ensureLoaded() }, [ensureLoaded])

  const step = stepStack[stepStack.length - 1]
  const groupIndex = STEP_GROUPS[step]
  const groupLabels = ['Type', supertype === 'digital' ? 'Platform' : 'Location', 'Search', 'Confirm details']
  const stepLabel = step === 'batchMode' ? 'Batch mode' : groupLabels[groupIndex]

  // Each step push also pushes a browser history entry (same /add route,
  // step recorded in location.state) so hardware/gesture "back" steps back
  // through the wizard instead of exiting /add — AddItem no longer remounts
  // AddFlow on location changes, so its candidates/selected/searchQuery
  // state survives across these pushes.
  const push = (name) => {
    const newStack = [...stepStack, name]
    setStepStack(newStack)
    navigate('.', { state: { stepStack: newStack } })
  }
  // Goes through browser history (rather than popping stepStack directly) so
  // the in-app back button and hardware/gesture back stay in sync — both
  // land on the popstate handler below.
  const back = () => {
    if (stepStack.length > 1) navigate(-1)
  }

  // Restores stepStack when the user navigates back/forward through the
  // history entries push() created above. Skips the initial mount and the
  // re-render caused by push()'s own navigate (which already applied the
  // same stepStack via setStepStack).
  useEffect(() => {
    if (location.key === lastSyncedKeyRef.current) return
    lastSyncedKeyRef.current = location.key
    setStepStack(location.state?.stepStack ?? initialStackRef.current)
  }, [location])

  // Persist the batch session (config + item list) so it survives a full
  // page reload; cleared as soon as batch mode is off.
  useEffect(() => {
    if (!batchMode) {
      sessionStorage.removeItem(SESSION_KEY)
      return
    }
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ batchMode, category, supertype, locationId, platformId, sessionItems })
    )
  }, [batchMode, category, supertype, locationId, platformId, sessionItems])

  const loadRecentItems = useCallback(async () => {
    try {
      const resp = await mediaApi.list({
        sort: 'created_at', order: 'desc', per_page: 10, page: 1,
        category, supertype,
      })
      setRecentItems(resp.items)
    } catch {
      // Best-effort — the "Recently added" panel just stays empty.
    }
  }, [category, supertype])

  useEffect(() => {
    if (!batchMode && (step === 'search' || step === 'digitalSearch')) loadRecentItems()
  }, [batchMode, step, loadRecentItems])

  const handleChangeCategory = (value) => {
    setCategory(value)
    if (supertype) push(supertype === 'physical' ? 'location' : 'platform')
  }

  const handleChangeSupertype = (value) => {
    setSupertype(value)
    if (category) push(value === 'physical' ? 'location' : 'platform')
  }

  const handleSelectLocation = (id) => {
    setLocationId(id)
    push('batchMode')
  }

  const handleSelectPlatform = (id) => {
    setPlatformId(id)
    push('batchMode')
  }

  const handleContinue = () => {
    push('batchMode')
  }

  const handleBatchContinue = () => {
    push(supertype === 'physical' ? 'search' : 'digitalSearch')
  }

  const selectCandidate = async (candidate) => {
    if (candidate.source === 'tmdb' && candidate.metadata?.tmdb_id) {
      setEnriching(true)
      try {
        const details = await lookupApi.tmdbDetails(candidate.metadata.tmdb_id, candidate.media_kind)
        candidate = { ...candidate, metadata: { ...candidate.metadata, ...details.metadata } }
      } catch {
        // Fall back to the partial metadata from search results — the user
        // can still fill in the rest of the form manually.
      } finally {
        setEnriching(false)
      }
    }
    setSelected(candidate)
    push('form')
  }

  const handleResults = (results) => {
    setCandidates(results)
    if (results.length === 0) return // stay on the search step
    if (results.length === 1) {
      selectCandidate(results[0])
    } else {
      push('edition')
    }
  }

  const handleManualAdd = () => {
    setSelected({ metadata: {} })
    push('form')
  }

  // In batch mode, saving an item returns straight to scanning — no
  // redirect to item detail/library, and the location/platform pre-fill
  // carries over to the next item via `locationId`/`platformId`. Outside
  // batch mode, behaviour is unchanged (parent navigates to item detail).
  const handleItemSaved = (item) => {
    if (batchMode) {
      const newStack = [supertype === 'physical' ? 'search' : 'digitalSearch']
      setSessionItems((items) => [item, ...items])
      setStepStack(newStack)
      // Replaces (rather than pushes) the current history entry — saving an
      // item returns to the search step "in place", it isn't a new step the
      // user should be able to back out of independently.
      navigate('.', { state: { stepStack: newStack }, replace: true })
      setSelected(null)
      setCandidates([])
      setSearchQuery('')
      navigator.vibrate?.(50)
    } else {
      onSaved(item)
    }
  }

  const handleExitBatch = () => {
    setBatchMode(false)
    setSessionItems([])
    sessionStorage.removeItem(SESSION_KEY)
    const slug = CATEGORIES.find((c) => c.value === category)?.slug
    navigate(slug ? `/library/${slug}` : '/library')
  }

  const handleItemEdited = (saved) => {
    if (batchMode) {
      setSessionItems((items) => items.map((it) => (it.id === saved.id ? saved : it)))
    } else {
      setRecentItems((items) => items.map((it) => (it.id === saved.id ? saved : it)))
    }
  }

  const itemListProps = {
    title: batchMode ? 'Added this session' : 'Recently added',
    items: batchMode ? sessionItems : recentItems,
    onItemClick: setEditingItem,
  }

  return (
    <div className="mx-auto max-w-xl py-4">
      {/* Header: back button + step progress */}
      <div className="flex items-center gap-2 mb-6">
        <Button
          variant="ghost"
          size="icon"
          onClick={back}
          disabled={stepStack.length === 1}
          className={clsx('-ml-2 shrink-0', stepStack.length === 1 && 'invisible')}
        >
          <ChevronRight size={18} className="rotate-180" />
        </Button>
        <div className="flex items-center gap-2 flex-1">
          {[0, 1, 2, 3].map((n) => (
            <div key={n} className="flex items-center gap-2 flex-1 last:flex-none">
              <div
                className={clsx(
                  'h-7 w-7 shrink-0 rounded-full flex items-center justify-center text-xs font-bold transition-colors',
                  groupIndex === n
                    ? 'bg-brand-600 text-white'
                    : groupIndex > n
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
                )}
              >
                {groupIndex > n ? '✓' : n + 1}
              </div>
              {n < 3 && <div className={clsx('h-px flex-1', groupIndex > n ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700')} />}
            </div>
          ))}
        </div>
        <div className="ml-2 text-xs text-gray-500 dark:text-gray-400 shrink-0">
          {stepLabel}
        </div>
      </div>

      {batchMode && groupIndex >= 2 && (
        <div className="mb-4">
          <BatchStatusBar
            supertype={supertype}
            locationId={locationId}
            platformId={platformId}
            locations={locations}
            platforms={platforms}
            onChangeLocation={() => setChangingLocation(true)}
            onExit={handleExitBatch}
          />
        </div>
      )}

      {enriching && <LoadingSpinner size="lg" className="py-12" />}

      {!enriching && step === 'type' && (
        <TypeStep
          category={category}
          supertype={supertype}
          onChangeCategory={handleChangeCategory}
          onChangeSupertype={handleChangeSupertype}
        />
      )}

      {!enriching && (step === 'location' || step === 'platform') && (
        <LocationOrPlatformStep
          supertype={supertype}
          locationId={locationId}
          platformId={platformId}
          onSelectLocation={handleSelectLocation}
          onSelectPlatform={handleSelectPlatform}
          onLocationCreated={setLocationId}
          onPlatformCreated={setPlatformId}
          onContinue={handleContinue}
        />
      )}

      {!enriching && step === 'batchMode' && (
        <BatchModeStep batchMode={batchMode} onChange={setBatchMode} onContinue={handleBatchContinue} />
      )}

      {!enriching && step === 'search' && (
        <div className="flex flex-col gap-4">
          <ScanOrSearch
            category={category}
            onResults={handleResults}
            batchMode={batchMode}
            query={searchQuery}
            onQueryChange={setSearchQuery}
            mediaKind={mediaKind}
            onMediaKindChange={setMediaKind}
          />
          <button
            onClick={handleManualAdd}
            className="text-sm text-center text-brand-600 dark:text-brand-400 hover:underline"
          >
            Add manually without searching →
          </button>
          <ItemListPanel {...itemListProps} />
        </div>
      )}

      {!enriching && step === 'digitalSearch' && (
        <div className="flex flex-col gap-4">
          <DigitalSearch
            category={category}
            onResults={handleResults}
            query={searchQuery}
            onQueryChange={setSearchQuery}
            mediaKind={mediaKind}
            onMediaKindChange={setMediaKind}
          />
          <button
            onClick={handleManualAdd}
            className="text-sm text-center text-brand-600 dark:text-brand-400 hover:underline"
          >
            Add manually without searching →
          </button>
          <ItemListPanel {...itemListProps} />
        </div>
      )}

      {!enriching && step === 'edition' && (
        <EditionSelector candidates={candidates} onSelect={selectCandidate} />
      )}

      {!enriching && step === 'form' && (
        <MetadataForm
          candidate={selected}
          category={category}
          supertype={supertype}
          locationId={locationId}
          platformId={platformId}
          onBack={back}
          onSaved={handleItemSaved}
        />
      )}

      {changingLocation && (
        <ChangeLocationModal
          supertype={supertype}
          locationId={locationId}
          platformId={platformId}
          onClose={() => setChangingLocation(false)}
          onChangeLocation={setLocationId}
          onChangePlatform={setPlatformId}
        />
      )}

      {editingItem && (
        <EditItemModal item={editingItem} onClose={() => setEditingItem(null)} onSaved={handleItemEdited} />
      )}
    </div>
  )
}
