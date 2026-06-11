import { useState, useEffect } from 'react'
import { ChevronRight, Plus } from 'lucide-react'
import Input, { Textarea, Select } from '../ui/Input'
import Button from '../ui/Button'
import { mediaApi } from '../../api/media'
import { locationsApi } from '../../api/locations'
import { platformsApi } from '../../api/platforms'
import { mediaSubtypesApi } from '../../api/mediaSubtypes'
import { matchPlatformLogo } from '../../lib/platformLogos'
import toast from 'react-hot-toast'

const NEW_PLATFORM = '__new__'

export default function MetadataForm({ candidate, category, supertype, onBack, onSaved }) {
  const [form, setForm] = useState(() => {
    const m = candidate?.metadata || {}
    return {
      title: m.title || candidate?.title || '',
      media_subtype_id: '',
      year: m.year || candidate?.year || '',
      genres: m.genres || '',
      description: m.description || '',
      cover_image_url: m.cover_image_url || candidate?.cover_url || '',
      barcode: m.barcode || '',
      edition: m.edition || candidate?.edition || '',
      notes: '',
      // Music
      artist: m.artist || '',
      label: m.label || '',
      track_count: m.track_count || '',
      // Films & TV
      director: m.director || '',
      studio: m.studio || '',
      runtime_minutes: m.runtime_minutes || '',
      rating: m.rating || '',
      seasons_owned: m.seasons_owned || '',
      episode_count: m.episode_count || '',
      // Books
      author: m.author || '',
      publisher: m.publisher || '',
      page_count: m.page_count || '',
      isbn: m.isbn || '',
      language: m.language || '',
      // IDs
      musicbrainz_id: m.musicbrainz_id || '',
      tmdb_id: m.tmdb_id || '',
      openlibrary_id: m.openlibrary_id || '',
      // Ownership
      location_id: '',
      platform_id: '',
    }
  })

  const [locations, setLocations] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [mediaSubtypes, setMediaSubtypes] = useState([])
  const [creatingPlatform, setCreatingPlatform] = useState(false)
  const [newPlatformName, setNewPlatformName] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    mediaSubtypesApi.list().then(setMediaSubtypes).catch(() => {})
    if (supertype === 'physical') locationsApi.list().then(setLocations).catch(() => {})
    if (supertype === 'digital') platformsApi.list().then(setPlatforms).catch(() => {})
  }, [supertype])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const subtypeOptions = mediaSubtypes
    .filter((s) => s.category === category && s.supertype === supertype)
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))

  // Auto-select the subtype when there's only one option for this category/supertype.
  useEffect(() => {
    if (form.media_subtype_id) return
    const opts = mediaSubtypes.filter((s) => s.category === category && s.supertype === supertype)
    if (opts.length === 1) set('media_subtype_id', String(opts[0].id))
  }, [mediaSubtypes, category, supertype]) // eslint-disable-line react-hooks/exhaustive-deps

  const flatLocations = []
  const flatten = (locs, depth = 0) => {
    for (const loc of locs) {
      flatLocations.push({ ...loc, depth })
      if (loc.children?.length) flatten(loc.children, depth + 1)
    }
  }
  flatten(locations)

  const handlePlatformChange = (e) => {
    const value = e.target.value
    if (value === NEW_PLATFORM) {
      setCreatingPlatform(true)
      return
    }
    set('platform_id', value)
  }

  const handleCreatePlatform = async () => {
    const name = newPlatformName.trim()
    if (!name) return
    try {
      const created = await platformsApi.create({ name, logo_key: matchPlatformLogo(name) })
      setPlatforms((p) => [...p, created].sort((a, b) => a.name.localeCompare(b.name)))
      set('platform_id', String(created.id))
      setCreatingPlatform(false)
      setNewPlatformName('')
      toast.success(`Platform "${created.name}" created`)
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleSave = async () => {
    if (!form.title.trim()) return toast.error('Title is required')
    if (!form.media_subtype_id) return toast.error('Please choose a type')
    setSaving(true)
    try {
      const payload = {
        ...form,
        media_subtype_id: Number(form.media_subtype_id),
        year: form.year ? Number(form.year) : null,
        track_count: form.track_count ? Number(form.track_count) : null,
        runtime_minutes: form.runtime_minutes ? Number(form.runtime_minutes) : null,
        episode_count: form.episode_count ? Number(form.episode_count) : null,
        page_count: form.page_count ? Number(form.page_count) : null,
        tmdb_id: form.tmdb_id ? Number(form.tmdb_id) : null,
        musicbrainz_id: form.musicbrainz_id || null,
        openlibrary_id: form.openlibrary_id || null,
        location_id: supertype === 'physical' && form.location_id ? Number(form.location_id) : null,
        platform_id: supertype === 'digital' && form.platform_id ? Number(form.platform_id) : null,
      }
      const saved = await mediaApi.create(payload)
      toast.success(`"${saved.title}" added to your collection!`)
      onSaved(saved)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ChevronRight size={18} className="rotate-180" />
        </Button>
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Confirm details</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Review and edit before saving</p>
        </div>
      </div>

      {/* Cover preview */}
      {form.cover_image_url && (
        <div className="flex justify-center">
          <img
            src={form.cover_image_url}
            alt={form.title}
            className="h-40 rounded-xl object-cover shadow-lg"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input label="Title *" value={form.title} onChange={(e) => set('title', e.target.value)} className="sm:col-span-2" />

        <Select label="Type *" value={form.media_subtype_id} onChange={(e) => set('media_subtype_id', e.target.value)}>
          <option value="">Select…</option>
          {subtypeOptions.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>

        <Input label="Year" type="number" value={form.year} onChange={(e) => set('year', e.target.value)} placeholder="2024" />

        {category === 'music' && <>
          <Input label="Artist" value={form.artist} onChange={(e) => set('artist', e.target.value)} />
          <Input label="Label" value={form.label} onChange={(e) => set('label', e.target.value)} />
          <Input label="Track count" type="number" value={form.track_count} onChange={(e) => set('track_count', e.target.value)} />
        </>}

        {category === 'films_tv' && <>
          <Input label="Director" value={form.director} onChange={(e) => set('director', e.target.value)} />
          <Input label="Studio" value={form.studio} onChange={(e) => set('studio', e.target.value)} />
          <Input label="Runtime (mins)" type="number" value={form.runtime_minutes} onChange={(e) => set('runtime_minutes', e.target.value)} />
          <Input label="Rating (e.g. PG-13)" value={form.rating} onChange={(e) => set('rating', e.target.value)} />
          <Input label="Seasons owned" value={form.seasons_owned} onChange={(e) => set('seasons_owned', e.target.value)} placeholder="e.g. 1–3" />
          <Input label="Episode count" type="number" value={form.episode_count} onChange={(e) => set('episode_count', e.target.value)} />
        </>}

        {category === 'books' && <>
          <Input label="Author" value={form.author} onChange={(e) => set('author', e.target.value)} />
          <Input label="Publisher" value={form.publisher} onChange={(e) => set('publisher', e.target.value)} />
          <Input label="ISBN" value={form.isbn} onChange={(e) => set('isbn', e.target.value)} />
          <Input label="Pages" type="number" value={form.page_count} onChange={(e) => set('page_count', e.target.value)} />
        </>}

        <Input label="Genre(s)" value={form.genres} onChange={(e) => set('genres', e.target.value)} placeholder="e.g. Rock, Alternative" />
        <Input label="Edition" value={form.edition} onChange={(e) => set('edition', e.target.value)} placeholder="e.g. Special Edition, 4K UHD" />

        <Input label="Barcode" value={form.barcode} onChange={(e) => set('barcode', e.target.value)} />

        {supertype === 'physical' && (
          <Select label="Location" value={form.location_id} onChange={(e) => set('location_id', e.target.value)}>
            <option value="">No location</option>
            {flatLocations.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {'  '.repeat(loc.depth)}{loc.name}
              </option>
            ))}
          </Select>
        )}

        {supertype === 'digital' && (
          <div className="flex flex-col gap-1">
            <Select label="Platform" value={form.platform_id} onChange={handlePlatformChange}>
              <option value="">No platform</option>
              {platforms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              <option value={NEW_PLATFORM}>+ Add new platform…</option>
            </Select>
            {creatingPlatform && (
              <div className="flex gap-2 mt-1">
                <Input
                  value={newPlatformName}
                  onChange={(e) => setNewPlatformName(e.target.value)}
                  placeholder="Platform name"
                  className="flex-1"
                  autoFocus
                />
                <Button type="button" size="icon" onClick={handleCreatePlatform}>
                  <Plus size={16} />
                </Button>
              </div>
            )}
          </div>
        )}

        <Input
          label="Cover image URL"
          value={form.cover_image_url}
          onChange={(e) => set('cover_image_url', e.target.value)}
          className="sm:col-span-2"
        />

        <Textarea
          label="Description"
          value={form.description}
          onChange={(e) => set('description', e.target.value)}
          rows={3}
          className="sm:col-span-2"
        />

        <Textarea
          label="Notes"
          value={form.notes}
          onChange={(e) => set('notes', e.target.value)}
          rows={2}
          className="sm:col-span-2"
          placeholder="Personal notes, condition, gift from…"
        />
      </div>

      <div className="flex gap-3 pt-2">
        <Button variant="secondary" onClick={onBack} className="flex-1">Back</Button>
        <Button onClick={handleSave} loading={saving} className="flex-1">
          Save to collection
        </Button>
      </div>
    </div>
  )
}
