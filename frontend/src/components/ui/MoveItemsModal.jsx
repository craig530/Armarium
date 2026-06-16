import { useState } from 'react'
import Modal from './Modal'
import Button from './Button'
import SelectMenu from './SelectMenu'

export default function MoveItemsModal({ open, onClose, type, item, locations, platforms, onMoveAndDelete }) {
  const [targetId, setTargetId] = useState('')
  const [busy, setBusy] = useState(false)

  const isLocation = type === 'location'

  // Platforms require a target (platform_id must be a valid id); locations allow null (unassign)
  const canConfirm = isLocation || !!targetId

  const handleConfirm = async () => {
    if (!canConfirm) return
    setBusy(true)
    try {
      await onMoveAndDelete(targetId ? Number(targetId) : null)
    } finally {
      setBusy(false)
      setTargetId('')
    }
  }

  const handleClose = () => {
    if (!busy) { setTargetId(''); onClose() }
  }

  if (!item) return null

  const count = item.item_count
  const typeName = isLocation ? 'location' : 'platform'

  const locationGroups = [{
    options: [
      { value: '', label: '— Remove location assignment —' },
      ...(locations || []).filter((l) => l.id !== item.id).map((l) => ({ value: String(l.id), label: l.path || l.name })),
    ],
  }]

  const platformGroups = [{
    options: [
      { value: '', label: '— Select a platform —' },
      ...(platforms || []).filter((p) => p.id !== item.id).map((p) => ({ value: String(p.id), label: p.name })),
    ],
  }]

  return (
    <Modal open={open} onClose={handleClose} title={`Delete "${item.name}"`}>
      <div className="space-y-4">
        <p className="text-sm text-gray-700 dark:text-gray-300">
          This {typeName} has <strong>{count} item{count === 1 ? '' : 's'}</strong>.
          Where should {count === 1 ? 'it' : 'they'} go before deleting?
        </p>

        {isLocation ? (
          <SelectMenu
            groups={locationGroups}
            value={targetId}
            onChange={setTargetId}
            className="w-full"
          />
        ) : (
          <SelectMenu
            groups={platformGroups}
            value={targetId}
            onChange={setTargetId}
            className="w-full"
          />
        )}

        <p className="text-xs text-gray-400 dark:text-gray-500">
          {targetId
            ? `All items will be moved, then "${item.name}" will be deleted.`
            : isLocation
            ? `Items will have their location removed, then "${item.name}" will be deleted.`
            : `Select a platform to move items to before deleting.`}
        </p>

        <div className="flex gap-2 justify-end">
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" size="sm" onClick={handleConfirm} disabled={busy || !canConfirm}>
            {busy ? 'Moving…' : 'Move & Delete'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
