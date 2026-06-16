import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Check, X, Lock } from 'lucide-react'
import { platformsApi } from '../../api/platforms'
import MoveItemsModal from '../ui/MoveItemsModal'
import { matchPlatformLogo, PLATFORM_LOGOS } from '../../lib/platformLogos'
import Input from '../ui/Input'
import Button from '../ui/Button'
import PlatformLogo from '../ui/PlatformLogo'
import LogoPicker from '../settings/LogoPicker'
import { useAuthStore, hasPermission, useReferenceDataStore } from '../../store'
import { useConfirm } from '../../hooks/useConfirm'
import toast from 'react-hot-toast'

const EMPTY_FORM = { name: '', logo_key: '', logo_url: null }

export default function PlatformManager() {
  const { user } = useAuthStore()
  const canManage = hasPermission(user, 'can_manage_platforms')
  const [platforms, setPlatforms] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [confirm, confirmDialog] = useConfirm()
  const [moveTarget, setMoveTarget] = useState(null)

  const load = () => {
    platformsApi.list().then(setPlatforms).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    if (!form.name.trim()) return toast.error('Name required')
    try {
      const payload = { name: form.name, logo_key: form.logo_key || null }
      if (editId) {
        await platformsApi.update(editId, payload)
        toast.success('Platform updated')
      } else {
        await platformsApi.create(payload)
        toast.success('Platform created')
      }
      setShowForm(false)
      setEditId(null)
      setForm(EMPTY_FORM)
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleEdit = (platform) => {
    setEditId(platform.id)
    setForm({ name: platform.name, logo_key: platform.logo_key || '', logo_url: platform.logo_url || null })
    setShowForm(true)
  }

  const handleDelete = async (platform) => {
    if (platform.item_count > 0) {
      setMoveTarget(platform)
      return
    }
    if (!await confirm(`Delete "${platform.name}"?`)) return
    try {
      await platformsApi.delete(platform.id)
      toast.success('Platform deleted')
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleMoveAndDelete = async (toPlatformId) => {
    if (!moveTarget) return
    const platform = moveTarget
    setMoveTarget(null)
    try {
      await platformsApi.moveItems(platform.id, toPlatformId)
      await platformsApi.delete(platform.id)
      toast.success('Platform deleted')
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleLogoUpload = async (file) => {
    if (!editId) return
    try {
      const updated = await platformsApi.uploadLogo(editId, file)
      setForm((f) => ({ ...f, logo_url: updated.logo_url }))
      toast.success('Logo uploaded')
      load()
      useReferenceDataStore.getState().invalidate()
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      {canManage && (
        <div className="flex items-center justify-end">
          <Button size="sm" onClick={() => { setEditId(null); setForm(EMPTY_FORM); setShowForm(true) }}>
            <Plus size={15} /> New platform
          </Button>
        </div>
      )}

      {/* Add/Edit form */}
      {canManage && showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {editId ? 'Edit platform' : 'New platform'}
          </h3>
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => {
              const name = e.target.value
              setForm((f) => ({
                ...f,
                name,
                logo_key: !editId && !f.logo_key ? (matchPlatformLogo(name) || '') : f.logo_key,
              }))
            }}
            placeholder="e.g. Netflix, Plex, Spotify"
            autoFocus
            list="platform-suggestions"
          />
          <datalist id="platform-suggestions">
            {Object.values(PLATFORM_LOGOS).map((p) => (
              <option key={p.label} value={p.label} />
            ))}
          </datalist>
          <LogoPicker
            logoKey={form.logo_key || null}
            logoUrl={form.logo_url}
            onSelect={(key) => setForm((f) => ({ ...f, logo_key: key || '' }))}
            onUpload={editId ? handleLogoUpload : undefined}
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleSave}>
              <Check size={14} /> Save
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
              <X size={14} /> Cancel
            </Button>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
      ) : platforms.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">No platforms yet.</p>
      ) : (
        <div className="space-y-1">
          {platforms.map((platform) => (
            <div key={platform.id} className="flex items-center gap-3 py-1.5">
              <PlatformLogo platform={platform} />
              <span className="flex-1 text-sm text-gray-800 dark:text-gray-200">{platform.name}</span>
              {platform.locked && (
                <Lock size={13} className="text-gray-400" title={platform.locked_reason} />
              )}
              {platform.item_count > 0 && (
                <span className="text-xs text-gray-400">{platform.item_count} items</span>
              )}
              {canManage && (
                <>
                  <button
                    onClick={() => handleEdit(platform)}
                    className="p-1 rounded-sm text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    <Pencil size={13} />
                  </button>
                  {!platform.locked && (
                    <button
                      onClick={() => handleDelete(platform)}
                      className="p-1 rounded-sm text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 dark:text-gray-500 pt-2 border-t border-gray-100 dark:border-gray-800">
        Platform logos are trademarks of their respective owners and are used here for identification purposes
        only, to help you recognise where your items are kept. Armarium is not affiliated with, endorsed by, or
        sponsored by any of these platforms.
      </p>

      {confirmDialog}

      <MoveItemsModal
        open={!!moveTarget}
        onClose={() => setMoveTarget(null)}
        type="platform"
        item={moveTarget}
        platforms={platforms}
        onMoveAndDelete={handleMoveAndDelete}
      />
    </div>
  )
}
