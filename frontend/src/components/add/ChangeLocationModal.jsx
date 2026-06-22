import { useState } from 'react'
import { Check, X } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input, { Select } from '../ui/Input'
import LocationPicker from '../locations/LocationPicker'
import IconPicker from '../settings/IconPicker'
import { locationsApi } from '../../api/locations'
import { platformsApi } from '../../api/platforms'
import { useAuthStore, useReferenceDataStore, hasPermission } from '../../store'
import { matchPlatformLogo } from '../../lib/platformLogos'
import toast from 'react-hot-toast'

// Batch-mode "Change location/platform" picker. Lets the user pick any
// existing location/platform for subsequent scans, and — if they hold the
// relevant Manage permission — quick-create a new one inline without
// leaving batch mode.
export default function ChangeLocationModal({ supertype, locationId, platformId, onClose, onChangeLocation, onChangePlatform }) {
  const isPhysical = supertype === 'physical'
  const { user } = useAuthStore()
  const { locations, platforms, invalidate, ensureLoaded } = useReferenceDataStore()
  const canManage = hasPermission(user, isPhysical ? 'can_manage_locations' : 'can_manage_platforms')

  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newParentId, setNewParentId] = useState(locationId || '')
  const [newIconKey, setNewIconKey] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    setSaving(true)
    try {
      if (isPhysical) {
        const created = await locationsApi.create({
          name,
          parent_id: newParentId ? Number(newParentId) : null,
          icon_key: newIconKey,
        })
        invalidate()
        await ensureLoaded()
        toast.success(`Location "${created.name}" created`)
        onChangeLocation(String(created.id))
        // Stay open and select the new location as the parent for the next
        // create — lets the user build out a hierarchy (e.g. Office > Shelf
        // > Top) in one go, instead of being dropped back to the item form
        // after every single location.
        setCreating(false)
        setNewName('')
        setNewParentId(String(created.id))
        setNewIconKey(null)
      } else {
        const created = await platformsApi.create({ name, logo_key: matchPlatformLogo(name) })
        invalidate()
        await ensureLoaded()
        toast.success(`Platform "${created.name}" created`)
        onChangePlatform(String(created.id))
        onClose()
      }
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={isPhysical ? 'Change location' : 'Change platform'}>
      <div className="flex flex-col gap-4">
        {!creating ? (
          <>
            {isPhysical ? (
              <LocationPicker
                label="Location"
                locations={locations}
                value={locationId}
                onChange={(value) => { if (value) { onChangeLocation(value); onClose() } }}
                placeholder="Select a location…"
              />
            ) : (
              <Select
                label="Platform"
                value={platformId || ''}
                onChange={(e) => { if (e.target.value) { onChangePlatform(e.target.value); onClose() } }}
              >
                <option value="">Select a platform…</option>
                {platforms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </Select>
            )}

            {canManage && (
              <button
                type="button"
                onClick={() => setCreating(true)}
                className="text-sm text-left text-brand-600 dark:text-brand-400 hover:underline"
              >
                + New {isPhysical ? 'location' : 'platform'}
              </button>
            )}
          </>
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
              <>
                <LocationPicker
                  label="Parent location (optional)"
                  locations={locations}
                  value={newParentId}
                  onChange={setNewParentId}
                  placeholder="No parent (top level)"
                />
                <IconPicker iconKey={newIconKey} iconUrl={null} onSelect={setNewIconKey} />
              </>
            )}
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCreate} loading={saving}>
                <Check size={14} /> Create &amp; select
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setCreating(false); setNewName('') }}>
                <X size={14} /> Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
