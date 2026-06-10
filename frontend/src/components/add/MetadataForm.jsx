import { useState, useEffect } from 'react'
import { ChevronRight, Upload } from 'lucide-react'
import Input, { Textarea, Select } from '../ui/Input'
import Button from '../ui/Button'
import { mediaApi } from '../../api/media'
import { locationsApi } from '../../api/locations'
import toast from 'react-hot-toast'

const MEDIA_TYPES = [
  { value: 'cd', label: 'CD' },
  { value: 'dvd', label: 'DVD' },
  { value: 'bluray', label: 'Blu-ray' },
  { value: 'book', label: 'Book' },
]

export default function MetadataForm({ candidate, onBack, onSaved }) {
  const [form, setForm] = useState(() => {
    const m = candidate?.metadata || {}
    return {
      title: m.title || '',
      media_type: m.media_type || candidate?.media_type || 'book',
      year: m.year || '',
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
      // Film
      director: m.director || '',
      studio: m.studio || '',
      runtime_minutes: m.runtime_minutes || '',
      rating: m.rating || '',
      // Book
      author: m.author || '',
      publisher: m.publisher || '',
      page_count: m.page_count || '',
      isbn: m.isbn || '',
      language: m.language || '',
      // IDs
      musicbrainz_id: m.musicbrainz_id || '',
      tmdb_id: m.tmdb_id || '',
      openlibrary_id: m.openlibrary_id || '',
      // Location
      location_id: '',
    }
  })

  const [locations, setLocations] = useState([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    locationsApi.list().then(setLocations).catch(() => {})
  }, [])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const flatLocations = []
  const flatten = (locs, depth = 0) => {
    for (const loc of locs) {
      flatLocations.push({ ...loc, depth })
      if (loc.children?.length) flatten(loc.children, depth + 1)
    }
  }
  flatten(locations)

  const handleSave = async () => {
    if (!form.title.trim()) return toast.error('Title is required')
    setSaving(true)
    try {
      const payload = {
        ...form,
        year: form.year ? Number(form.year) : null,
        track_count: form.track_count ? Number(form.track_count) : null,
        runtime_minutes: form.runtime_minutes ? Number(form.runtime_minutes) : null,
        page_count: form.page_count ? Number(form.page_count) : null,
        tmdb_id: form.tmdb_id ? Number(form.tmdb_id) : null,
        location_id: form.location_id ? Number(form.location_id) : null,
        musicbrainz_id: form.musicbrainz_id || null,
        openlibrary_id: form.openlibrary_id || null,
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

  const type = form.media_type

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

        <Select label="Type" value={form.media_type} onChange={(e) => set('media_type', e.target.value)}>
          {MEDIA_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </Select>

        <Input label="Year" type="number" value={form.year} onChange={(e) => set('year', e.target.value)} placeholder="2024" />

        {(type === 'cd') && <>
          <Input label="Artist" value={form.artist} onChange={(e) => set('artist', e.target.value)} />
          <Input label="Label" value={form.label} onChange={(e) => set('label', e.target.value)} />
          <Input label="Track count" type="number" value={form.track_count} onChange={(e) => set('track_count', e.target.value)} />
        </>}

        {(type === 'dvd' || type === 'bluray') && <>
          <Input label="Director" value={form.director} onChange={(e) => set('director', e.target.value)} />
          <Input label="Studio" value={form.studio} onChange={(e) => set('studio', e.target.value)} />
          <Input label="Runtime (mins)" type="number" value={form.runtime_minutes} onChange={(e) => set('runtime_minutes', e.target.value)} />
          <Input label="Rating (e.g. PG-13)" value={form.rating} onChange={(e) => set('rating', e.target.value)} />
        </>}

        {type === 'book' && <>
          <Input label="Author" value={form.author} onChange={(e) => set('author', e.target.value)} />
          <Input label="Publisher" value={form.publisher} onChange={(e) => set('publisher', e.target.value)} />
          <Input label="ISBN" value={form.isbn} onChange={(e) => set('isbn', e.target.value)} />
          <Input label="Pages" type="number" value={form.page_count} onChange={(e) => set('page_count', e.target.value)} />
        </>}

        <Input label="Genre(s)" value={form.genres} onChange={(e) => set('genres', e.target.value)} placeholder="e.g. Rock, Alternative" />
        <Input label="Edition" value={form.edition} onChange={(e) => set('edition', e.target.value)} placeholder="e.g. Special Edition, 4K UHD" />

        <Input label="Barcode" value={form.barcode} onChange={(e) => set('barcode', e.target.value)} />

        <Select label="Location" value={form.location_id} onChange={(e) => set('location_id', e.target.value)}>
          <option value="">No location</option>
          {flatLocations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {'  '.repeat(loc.depth)}{loc.name}
            </option>
          ))}
        </Select>

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
