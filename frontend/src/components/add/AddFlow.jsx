import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
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
import ListNameStep from './ListNameStep'
import ListItemsStep from './ListItemsStep'
import LoadingSpinner from '../ui/LoadingSpinner'
import Button from '../ui/Button'
import { lookupApi } from '../../api/lookup'
import { mediaApi } from '../../api/media'
import { useReferenceDataStore, useLibraryStore } from '../../store'
import { useStepHistory } from '../../hooks/useStepHistory'
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
// type -> listName -> listItems (the "List" branch — see handleSelectListMode)
const STEP_GROUPS = {
  type: 0,
  location: 1,
  platform: 1,
  batchMode: 1,
  listName: 1,
  search: 2,
  digitalSearch: 2,
  edition: 2,
  listItems: 2,
  form: 3,
}

export default function AddFlow({ onSaved }) {
  const navigate = useNavigate()
  const restored = loadBatchSession()

  // Tracks the wizard's step stack alongside browser history, so
  // hardware/gesture "back" steps back through the wizard instead of
  // exiting /add — see useStepHistory for details. AddItem no longer
  // remounts AddFlow on location changes, so the rest of this component's
  // state (candidates/selected/searchQuery etc.) survives these in-place
  // navigations.
  const { stack: stepStack, push, back, replaceStack } = useStepHistory(
    restored ? [restored.supertype === 'physical' ? 'search' : 'digitalSearch'] : ['type']
  )
  const [category, setCategory] = useState(restored?.category ?? null)
  const [supertype, setSupertype] = useState(restored?.supertype ?? null)
  const [locationId, setLocationId] = useState(restored?.locationId ?? '')
  const [platformId, setPlatformId] = useState(restored?.platformId ?? '')
  const [batchMode, setBatchMode] = useState(restored?.batchMode ?? false)
  const [creatingList, setCreatingList] = useState(false)
  const [newList, setNewList] = useState(null)
  const [batchListId, setBatchListId] = useState('')
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

  const { locations, platforms, lists, appConfig, ensureLoaded } = useReferenceDataStore()
  useEffect(() => { ensureLoaded() }, [ensureLoaded])

  const disabledCategories = appConfig?.disabled_categories ?? []
  const enabledCategories = CATEGORIES.filter((c) => !disabledCategories.includes(c.value))

  const step = stepStack[stepStack.length - 1]
  const groupIndex = STEP_GROUPS[step]
  const groupLabels = creatingList
    ? ['Type', 'Name', 'Items', '']
    : ['Type', supertype === 'digital' ? 'Platform' : 'Location', 'Search', 'Confirm details']
  const stepLabel = step === 'batchMode' ? 'Batch mode' : groupLabels[groupIndex]
  // Don't show step dots on the type step until the user makes a selection
  const showStepProgress = step !== 'type' || supertype !== null || creatingList

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
    if (creatingList) {
      push('listName')
    } else if (supertype) {
      push(supertype === 'physical' ? 'location' : 'platform')
    }
  }

  const handleChangeSupertype = (value) => {
    setSupertype(value)
    setCreatingList(false)
    if (category) push(value === 'physical' ? 'location' : 'platform')
  }

  // Third option alongside Physical/Digital on the type step — branches into
  // the listName -> listItems steps instead of location/platform -> search.
  const handleSelectListMode = () => {
    setCreatingList(true)
    setSupertype(null)
    if (category) push('listName')
  }

  const handleListCreated = (list) => {
    setNewList(list)
    push('listItems')
  }

  // Mirrors handleExitBatch's navigation: land on the category's library
  // view, pre-filtered to the list just populated.
  const handleListItemsDone = () => {
    useLibraryStore.getState().setFilter('list_id', String(newList.id))
    const slug = CATEGORIES.find((c) => c.value === category)?.slug
    navigate(slug ? `/library/${slug}` : '/library')
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
      setSessionItems((items) => [item, ...items])
      replaceStack([supertype === 'physical' ? 'search' : 'digitalSearch'])
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
        {showStepProgress ? (
          <>
            <div className="flex items-center gap-2 flex-1">
              {(creatingList ? [0, 1, 2] : [0, 1, 2, 3]).map((n, idx, arr) => (
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
                  {idx < arr.length - 1 && <div className={clsx('h-px flex-1', groupIndex > n ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700')} />}
                </div>
              ))}
            </div>
            <div className="ml-2 text-xs text-gray-500 dark:text-gray-400 shrink-0">
              {stepLabel}
            </div>
          </>
        ) : (
          <div className="flex-1" />
        )}
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
          creatingList={creatingList}
          onChangeCategory={handleChangeCategory}
          onChangeSupertype={handleChangeSupertype}
          onSelectList={handleSelectListMode}
          categories={enabledCategories}
        />
      )}

      {!enriching && step === 'listName' && (
        <ListNameStep category={category} onBack={back} onCreated={handleListCreated} />
      )}

      {!enriching && step === 'listItems' && newList && (
        <ListItemsStep list={newList} onBack={back} onDone={handleListItemsDone} />
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
        <BatchModeStep
          batchMode={batchMode}
          onChange={setBatchMode}
          onContinue={handleBatchContinue}
          category={category}
          lists={lists}
          batchListId={batchListId}
          onBatchListChange={setBatchListId}
        />
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
          defaultListIds={batchListId ? [Number(batchListId)] : []}
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
