import clsx from 'clsx'
import Button from '../ui/Button'
import { Select } from '../ui/Input'

// Inserted between the location/platform step and search/scan. Batch mode
// stays off by default — once enabled it persists for the rest of the
// session (see AddFlow's sessionStorage-backed restore) until the user taps
// "Exit batch" on the status bar.
export default function BatchModeStep({ batchMode, onChange, onContinue, category, lists = [], batchListId, onBatchListChange }) {
  const categoryLists = lists.filter((l) => l.category === category)
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Batch mode</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Cataloguing a whole shelf? Turn on batch mode to save each item the moment you confirm
          it and jump straight back to scanning, no need to repeat this setup for every item.
        </p>
      </div>

      <button
        type="button"
        onClick={() => onChange(!batchMode)}
        className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 dark:border-gray-700 p-4 text-left"
      >
        <div>
          <p className="font-medium text-gray-900 dark:text-white">Enable batch mode</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Stays on until you exit batch mode</p>
        </div>
        <div
          role="switch"
          aria-checked={batchMode}
          className={clsx(
            'relative h-6 w-11 shrink-0 rounded-full transition-colors',
            batchMode ? 'bg-brand-600' : 'bg-gray-300 dark:bg-gray-700'
          )}
        >
          <div
            className={clsx(
              'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform',
              batchMode && 'translate-x-5'
            )}
          />
        </div>
      </button>

      {categoryLists.length > 0 && (
        <div>
          <Select
            label="Default list (optional)"
            value={batchListId || ''}
            onChange={(e) => onBatchListChange(e.target.value)}
          >
            <option value="">No list</option>
            {categoryLists.map((l) => (
              <option key={l.id} value={String(l.id)}>{l.name}</option>
            ))}
          </Select>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Each item saved this session will be added to this list.
          </p>
        </div>
      )}

      <Button onClick={onContinue} className="w-full">Continue</Button>
    </div>
  )
}
