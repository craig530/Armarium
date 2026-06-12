import { useState, useCallback } from 'react'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'

// Replaces `window.confirm()`, which silently does nothing — no dialog, and
// returns `false` immediately — in an iOS "Add to Home Screen" standalone
// PWA (this app's manifest.json sets `"display": "standalone"`). Returns
// `[confirm, dialog]`: call `confirm(message)` for a promise resolving to
// true/false, and render `dialog` once near the top of the component tree.
export function useConfirm() {
  const [state, setState] = useState(null)

  const confirm = useCallback((message) => new Promise((resolve) => {
    setState({ message, resolve })
  }), [])

  const resolve = (result) => {
    state?.resolve(result)
    setState(null)
  }

  const dialog = state && (
    <Modal open title="Confirm" onClose={() => resolve(false)}>
      <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 whitespace-pre-line">{state.message}</p>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={() => resolve(false)}>Cancel</Button>
        <Button variant="danger" onClick={() => resolve(true)}>Delete</Button>
      </div>
    </Modal>
  )

  return [confirm, dialog]
}
