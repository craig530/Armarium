import { useState } from 'react'
import ScanOrSearch from './ScanOrSearch'
import EditionSelector from './EditionSelector'
import MetadataForm from './MetadataForm'

// Step 1: scan/search → results (array of candidates)
// Step 2: user picks an edition → selected candidate
// Step 3: confirm/edit metadata → save
// After save: navigate away

export default function AddFlow({ onSaved }) {
  const [step, setStep] = useState(1)
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)
  const [mediaType, setMediaType] = useState('book')

  const handleResults = (results, type) => {
    setMediaType(type)
    setCandidates(results)
    if (results.length === 0) return   // stay on step 1
    if (results.length === 1) {
      // Skip selection step
      setSelected(results[0])
      setStep(3)
    } else {
      setStep(2)
    }
  }

  const handleSelect = (candidate) => {
    setSelected(candidate)
    setStep(3)
  }

  const handleManualAdd = () => {
    setSelected({ metadata: { media_type: mediaType }, media_type: mediaType })
    setStep(3)
  }

  return (
    <div className="mx-auto max-w-xl py-4">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {[1, 2, 3].map((n) => (
          <div key={n} className="flex items-center gap-2">
            <div
              className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                step === n
                  ? 'bg-brand-600 text-white'
                  : step > n
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
              }`}
            >
              {step > n ? '✓' : n}
            </div>
            {n < 3 && <div className={`h-px flex-1 w-8 ${step > n ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}`} />}
          </div>
        ))}
        <div className="ml-2 text-xs text-gray-500 dark:text-gray-400">
          {step === 1 ? 'Search' : step === 2 ? 'Select edition' : 'Confirm details'}
        </div>
      </div>

      {step === 1 && (
        <div className="flex flex-col gap-4">
          <ScanOrSearch onResults={handleResults} />
          <button
            onClick={handleManualAdd}
            className="text-sm text-center text-brand-600 dark:text-brand-400 hover:underline"
          >
            Add manually without searching →
          </button>
        </div>
      )}

      {step === 2 && (
        <EditionSelector
          candidates={candidates}
          onSelect={handleSelect}
          onBack={() => setStep(1)}
        />
      )}

      {step === 3 && (
        <MetadataForm
          candidate={selected}
          onBack={() => setStep(candidates.length > 1 ? 2 : 1)}
          onSaved={onSaved}
        />
      )}
    </div>
  )
}
