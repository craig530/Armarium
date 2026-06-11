import { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import Button from '../ui/Button'
import Input, { Select } from '../ui/Input'
import LoadingSpinner from '../ui/LoadingSpinner'
import LocationPicker from '../locations/LocationPicker'
import { locationsApi } from '../../api/locations'
import { platformsApi } from '../../api/platforms'
import { matchPlatformLogo } from '../../lib/platformLogos'
import toast from 'react-hot-toast'

// Mandatory pre-step before search/manual entry: physical items must be
// assigned a Location, digital items must be assigned a Platform. Both
// support inline quick-create, which auto-selects the new entity and
// advances the flow — there is no way to skip this step with an empty
// selection (AddFlow's handlers ignore empty ids).
export default function LocationOrPlatformStep({ supertype, locationId, platformId, onSelectLocation, onSelectPlatform }) {
  const isPhysical = supertype === 'physical'
  const [locations, setLocations] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newParentId, setNewParentId] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setLoading(true)
    if (isPhysical) {
      locationsApi.list().then(setLocations).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
    } else {
      platformsApi.list().then(setPlatforms).catch((err) => toast.error(err.message)).finally(() => setLoading(false))
    }
  }, [isPhysical])

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    setSaving(true)
    try {
      if (isPhysical) {
        const created = await locationsApi.create({
          name,
          parent_id: newParentId ? Number(newParentId) : null,
          icon_key: null,
        })
        setLocations(await locationsApi.list())
        toast.success(`Location "${created.name}" created`)
        onSelectLocation(String(created.id))
      } else {
        const created = await platformsApi.create({ name, logo_key: matchPlatformLogo(name) })
        setPlatforms((p) => [...p, created].sort((a, b) => a.name.localeCompare(b.name)))
        toast.success(`Platform "${created.name}" created`)
        onSelectPlatform(String(created.id))
      }
      setCreating(false)
      setNewName('')
      setNewParentId('')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          {isPhysical ? 'Where will this be kept?' : 'Where will you access this?'}
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {isPhysical
            ? 'Choose a location for this item, or create a new one.'
            : 'Choose a platform for this item, or create a new one.'}
        </p>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" className="py-8" />
      ) : (
        <>
          {isPhysical ? (
            <LocationPicker
              label="Location"
              locations={locations}
              value={locationId}
              onChange={(value) => { if (value) onSelectLocation(value) }}
              placeholder="Select a location…"
            />
          ) : (
            <Select
              label="Platform"
              value={platformId || ''}
              onChange={(e) => { if (e.target.value) onSelectPlatform(e.target.value) }}
            >
              <option value="">Select a platform…</option>
              {platforms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
          )}

          {!creating ? (
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="text-sm text-left text-brand-600 dark:text-brand-400 hover:underline"
            >
              + Create new {isPhysical ? 'location' : 'platform'}
            </button>
          ) : (
            <div className="flex flex-col gap-3 rounded-xl border border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-900">
              <Input
                label={isPhysical ? 'Location name' : 'Platform name'}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder={isPhysical ? 'e.g. Bookshelf, Living Room' : 'e.g. Netflix, Spotify'}
                autoFocus
              />
              {isPhysical && (
                <LocationPicker
                  label="Parent location (optional)"
                  locations={locations}
                  value={newParentId}
                  onChange={setNewParentId}
                  placeholder="— No parent (top level) —"
                />
              )}
              <div className="flex gap-2">
                <Button size="sm" onClick={handleCreate} loading={saving}>
                  <Check size={14} /> Create &amp; select
                </Button>
                <Button size="sm" variant="ghost" onClick={() => { setCreating(false); setNewName(''); setNewParentId('') }}>
                  <X size={14} /> Cancel
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
