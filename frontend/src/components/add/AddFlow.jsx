import { useState } from 'react'
import TypeStep from './TypeStep'
import ScanOrSearch from './ScanOrSearch'
import EditionSelector from './EditionSelector'
import MetadataForm from './MetadataForm'

// Step 1: Physical/digital + category
// Step 2: scan/search → results (array of candidates)
// Step 3: user picks an edition → selected candidate
// Step 4: confirm/edit metadata → save
// After save: navigate away

const STEP_LABELS = ['Type', 'Search', 'Select edition', 'Confirm details']

export default function AddFlow({ onSaved }) {
  const [step, setStep] = useState(1)
  const [category, setCategory] = useState(null)
  const [supertype, setSupertype] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)

  const handleChangeCategory = (value) => {
    setCategory(value)
    if (supertype) setStep(2)
  }

  const handleChangeSupertype = (value) => {
    setSupertype(value)
    if (category) setStep(2)
  }

  const handleResults = (results) => {
    setCandidates(results)
    if (results.length === 0) return   // stay on step 2
    if (results.length === 1) {
      // Skip selection step
      setSelected(results[0])
      setStep(4)
    } else {
      setStep(3)
    }
  }

  const handleSelect = (candidate) => {
    setSelected(candidate)
    setStep(4)
  }

  const handleManualAdd = () => {
    setSelected({ metadata: {} })
    setStep(4)
  }

  return (
    <div className="mx-auto max-w-xl py-4">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {[1, 2, 3, 4].map((n) => (
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
            {n < 4 && <div className={`h-px flex-1 w-8 ${step > n ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}`} />}
          </div>
        ))}
        <div className="ml-2 text-xs text-gray-500 dark:text-gray-400">
          {STEP_LABELS[step - 1]}
        </div>
      </div>

      {step === 1 && (
        <TypeStep
          category={category}
          supertype={supertype}
          onChangeCategory={handleChangeCategory}
          onChangeSupertype={handleChangeSupertype}
        />
      )}

      {step === 2 && (
        <div className="flex flex-col gap-4">
          <ScanOrSearch category={category} onResults={handleResults} />
          <button
            onClick={handleManualAdd}
            className="text-sm text-center text-brand-600 dark:text-brand-400 hover:underline"
          >
            Add manually without searching →
          </button>
          <button
            onClick={() => setStep(1)}
            className="text-xs text-center text-gray-400 hover:underline"
          >
            ← Change category or type
          </button>
        </div>
      )}

      {step === 3 && (
        <EditionSelector
          candidates={candidates}
          onSelect={handleSelect}
          onBack={() => setStep(2)}
        />
      )}

      {step === 4 && (
        <MetadataForm
          candidate={selected}
          category={category}
          supertype={supertype}
          onBack={() => setStep(candidates.length > 1 ? 3 : 2)}
          onSaved={onSaved}
        />
      )}
    </div>
  )
}
