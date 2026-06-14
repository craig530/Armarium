import { useState, useCallback } from 'react'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'

// Replaces `window.confirm()`, which silently does nothing — no dialog, and
// returns `false` immediately — in an iOS "Add to Home Screen" standalone
// PWA (this app's manifest.json sets `"display": "standalone"`). Returns
// `[confirm, dialog]`: call `confirm(message, options)` for a promise
// resolving to true/false, and render `dialog` once near the top of the
// component tree.
//
// `options`:
//   - `title`: dialog heading (default "Confirm")
//   - `confirmLabel` / `cancelLabel`: button text (defaults "Delete"/"Cancel")
//   - `variant`: confirm button variant (default "danger")
//   - `requireText`: if set, the confirm button stays disabled until the
//     user types this exact text — for an extra step on irreversible actions
export function useConfirm() {
  const [state, setState] = useState(null)
  const [typed, setTyped] = useState('')

  const confirm = useCallback((message, options = {}) => new Promise((resolve) => {
    setTyped('')
    setState({ message, resolve, ...options })
  }), [])

  const resolve = (result) => {
    state?.resolve(result)
    setState(null)
    setTyped('')
  }

  const requireText = state?.requireText
  const canConfirm = !requireText || typed === requireText

  const dialog = state && (
    <Modal open title={state.title || 'Confirm'} onClose={() => resolve(false)}>
      <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 whitespace-pre-line">{state.message}</p>
      {requireText && (
        <Input
          label={`Type "${requireText}" to confirm`}
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          autoFocus
          className="mb-4"
        />
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={() => resolve(false)}>{state.cancelLabel || 'Cancel'}</Button>
        <Button variant={state.variant || 'danger'} disabled={!canConfirm} onClick={() => resolve(true)}>
          {state.confirmLabel || 'Delete'}
        </Button>
      </div>
    </Modal>
  )

  return [confirm, dialog]
}
