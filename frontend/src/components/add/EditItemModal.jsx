import Modal from '../ui/Modal'
import MetadataForm from './MetadataForm'

// Wraps the edit-capable MetadataForm in a modal/sheet over the scan screen.
// Save/Cancel both just close the modal — the underlying AddFlow/batch state
// (step stack, session items, location/platform) is untouched.
export default function EditItemModal({ item, onClose, onSaved }) {
  return (
    <Modal open onClose={onClose} title="Edit item">
      <MetadataForm
        item={item}
        category={item.category}
        supertype={item.supertype}
        onCancel={onClose}
        onSaved={(saved) => { onSaved(saved); onClose() }}
      />
    </Modal>
  )
}
