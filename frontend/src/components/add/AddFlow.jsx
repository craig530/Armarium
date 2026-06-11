import { useState } from 'react'
import clsx from 'clsx'
import { ChevronRight } from 'lucide-react'
import TypeStep from './TypeStep'
import LocationOrPlatformStep from './LocationOrPlatformStep'
import ScanOrSearch from './ScanOrSearch'
import DigitalSearch from './DigitalSearch'
import EditionSelector from './EditionSelector'
import MetadataForm from './MetadataForm'
import LoadingSpinner from '../ui/LoadingSpinner'
import Button from '../ui/Button'
import { lookupApi } from '../../api/lookup'

// Each step is only ever pushed onto the stack when it's actually shown, so
// `back()` (pop) always returns to wherever the user really came from —
// e.g. a single-result search skips `edition` entirely, so going back from
// `form` returns straight to `search`/`digitalSearch`.
//
// type -> location | platform -> search | digitalSearch -> [edition] -> form
const STEP_GROUPS = {
  type: 0,
  location: 1,
  platform: 1,
  search: 2,
  digitalSearch: 2,
  edition: 2,
  form: 3,
}

export default function AddFlow({ onSaved }) {
  const [stepStack, setStepStack] = useState(['type'])
  const [category, setCategory] = useState(null)
  const [supertype, setSupertype] = useState(null)
  const [locationId, setLocationId] = useState('')
  const [platformId, setPlatformId] = useState('')
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)
  const [enriching, setEnriching] = useState(false)

  const step = stepStack[stepStack.length - 1]
  const groupIndex = STEP_GROUPS[step]
  const groupLabels = ['Type', supertype === 'digital' ? 'Platform' : 'Location', 'Search', 'Confirm details']

  const push = (name) => setStepStack((s) => [...s, name])
  const back = () => setStepStack((s) => (s.length > 1 ? s.slice(0, -1) : s))

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
    push('search')
  }

  const handleSelectPlatform = (id) => {
    setPlatformId(id)
    push('digitalSearch')
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
          {groupLabels[groupIndex]}
        </div>
      </div>

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
        />
      )}

      {!enriching && step === 'search' && (
        <div className="flex flex-col gap-4">
          <ScanOrSearch category={category} onResults={handleResults} />
          <button
            onClick={handleManualAdd}
            className="text-sm text-center text-brand-600 dark:text-brand-400 hover:underline"
          >
            Add manually without searching →
          </button>
        </div>
      )}

      {!enriching && step === 'digitalSearch' && (
        <div className="flex flex-col gap-4">
          <DigitalSearch category={category} onResults={handleResults} />
          <button
            onClick={handleManualAdd}
            className="text-sm text-center text-brand-600 dark:text-brand-400 hover:underline"
          >
            Add manually without searching →
          </button>
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
          onSaved={onSaved}
        />
      )}
    </div>
  )
}
