import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Check, X, Tv } from 'lucide-react'
import { platformsApi } from '../../api/platforms'
import { platformLogoUrl, matchPlatformLogo, PLATFORM_LOGOS } from '../../lib/platformLogos'
import Input from '../ui/Input'
import Button from '../ui/Button'
import toast from 'react-hot-toast'

function PlatformLogo({ platform, className = 'h-8 w-8' }) {
  const url = platformLogoUrl(platform)
  return (
    <div className={`shrink-0 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden p-1 ${className}`}>
      {url ? (
        <img src={url} alt="" className="h-full w-full object-contain" />
      ) : (
        <Tv size={16} className="text-gray-400" />
      )}
    </div>
  )
}

export default function PlatformManager() {
  const [platforms, setPlatforms] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)
  const [form, setForm] = useState({ name: '' })

  const load = () => {
    platformsApi.list().then(setPlatforms).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    if (!form.name.trim()) return toast.error('Name required')
    try {
      if (editId) {
        await platformsApi.update(editId, { name: form.name })
        toast.success('Platform updated')
      } else {
        const matched = matchPlatformLogo(form.name)
        await platformsApi.create({ name: form.name, logo_key: matched })
        toast.success('Platform created')
      }
      setShowForm(false)
      setEditId(null)
      setForm({ name: '' })
      load()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleEdit = (platform) => {
    setEditId(platform.id)
    setForm({ name: platform.name })
    setShowForm(true)
  }

  const handleDelete = async (platform) => {
    if (!confirm(`Delete "${platform.name}"?`)) return
    try {
      await platformsApi.delete(platform.id)
      toast.success('Platform deleted')
      load()
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Manage platforms</h2>
        <Button size="sm" onClick={() => { setEditId(null); setForm({ name: '' }); setShowForm(true) }}>
          <Plus size={15} /> New platform
        </Button>
      </div>

      <p className="text-sm text-gray-500 dark:text-gray-400 -mt-4">
        Streaming and digital services for your library, e.g. Netflix, Plex, Spotify.
      </p>

      {/* Add/Edit form */}
      {showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {editId ? 'Edit platform' : 'New platform'}
          </h3>
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Netflix, Plex, Spotify"
            autoFocus
            list="platform-suggestions"
          />
          <datalist id="platform-suggestions">
            {Object.values(PLATFORM_LOGOS).map((p) => (
              <option key={p.label} value={p.label} />
            ))}
          </datalist>
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
              {platform.item_count > 0 && (
                <span className="text-xs text-gray-400">{platform.item_count} items</span>
              )}
              <button
                onClick={() => handleEdit(platform)}
                className="p-1 rounded text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <Pencil size={13} />
              </button>
              <button
                onClick={() => handleDelete(platform)}
                className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
