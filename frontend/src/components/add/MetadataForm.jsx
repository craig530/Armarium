import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import Input, { Textarea, Select } from '../ui/Input'
import Button from '../ui/Button'
import SelectMenu from '../ui/SelectMenu'
import PlatformLogo from '../ui/PlatformLogo'
import LocationPicker from '../locations/LocationPicker'
import ListsMultiSelect from '../lists/ListsMultiSelect'
import { mediaApi } from '../../api/media'
import { platformsApi } from '../../api/platforms'
import { coverProxyUrl } from '../../api/lookup'
import { useReferenceDataStore } from '../../store'
import { matchPlatformLogo } from '../../lib/platformLogos'
import toast from 'react-hot-toast'

const NEW_PLATFORM = '__new__'

// Best-guess subtype name for a given category/supertype (and, for TMDB
// results, movie vs TV), checked before falling back to "exactly 1 option".
// Formats that come in multiple flavours (DVD vs Blu-ray, Book vs Graphic
// Novel, eBook vs Audiobook) aren't derivable from lookup metadata and are
// left for the user to pick.
const AUTO_SUBTYPE_NAME = {
  'films_tv:digital:movie': 'Film',
  'films_tv:digital:tv': 'TV Series',
  'music:digital': 'Music',
  'books:digital': 'eBook',
  'books:physical': 'Book',
  'games:digital': 'Nintendo eShop',
  'games:physical': 'Nintendo Switch',
}

// `item` switches the form into edit mode: fields are seeded from the
// existing item (rather than a lookup `candidate`), Save does a PUT instead
// of a POST, and `onCancel` replaces `onBack`. Used both by the Add flow
// (create) and the batch-mode/"Recently added" edit modal (update).
export default function MetadataForm({ candidate, item, category, supertype, locationId, platformId, defaultListIds = [], onBack, onCancel, onSaved }) {
  const isEdit = !!item

  const [form, setForm] = useState(() => {
    if (isEdit) {
      return {
        title: item.title || '',
        media_subtype_id: item.media_subtype_id != null ? String(item.media_subtype_id) : '',
        year: item.year || '',
        genres: item.genres || '',
        description: item.description || '',
        cover_image_url: item.cover_image_url || '',
        barcode: item.barcode || '',
        edition: item.edition || '',
        notes: item.notes || '',
        // Music
        artist: item.artist || '',
        label: item.label || '',
        track_count: item.track_count || '',
        // Films & TV
        director: item.director || '',
        studio: item.studio || '',
        runtime_minutes: item.runtime_minutes || '',
        rating: item.rating || '',
        seasons_owned: item.seasons_owned || '',
        episode_count: item.episode_count || '',
        // Books
        author: item.author || '',
        publisher: item.publisher || '',
        page_count: item.page_count || '',
        isbn: item.isbn || '',
        language: item.language || '',
        // Games
        developer: item.developer || '',
        igdb_id: item.igdb_id || '',
        // IDs
        musicbrainz_id: item.musicbrainz_id || '',
        tmdb_id: item.tmdb_id || '',
        openlibrary_id: item.openlibrary_id || '',
        // Ownership
        location_id: item.location_id != null ? String(item.location_id) : '',
        platform_id: item.platform_id != null ? String(item.platform_id) : '',
        list_ids: item.list_ids || [],
      }
    }

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
      tmdb_rating: m.tmdb_rating ?? null,
      // Books
      author: m.author || '',
      publisher: m.publisher || '',
      page_count: m.page_count || '',
      isbn: m.isbn || '',
      language: m.language || '',
      // Games
      developer: m.developer || '',
      igdb_id: m.igdb_id || '',
      // IDs
      musicbrainz_id: m.musicbrainz_id || '',
      tmdb_id: m.tmdb_id || '',
      openlibrary_id: m.openlibrary_id || '',
      // Ownership
      location_id: locationId || '',
      platform_id: platformId || '',
      list_ids: [...defaultListIds],
    }
  })

  const { locations, platforms, mediaSubtypes, ensureLoaded, invalidate } = useReferenceDataStore()
  const [creatingPlatform, setCreatingPlatform] = useState(false)
  const [newPlatformName, setNewPlatformName] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { ensureLoaded() }, [ensureLoaded])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const subtypeOptions = mediaSubtypes
    .filter((s) => s.category === category && s.supertype === supertype)
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))

  // Auto-select the subtype: prefer a best-guess match based on the lookup
  // result (e.g. TMDB movie vs TV), then fall back to the only option when
  // there's exactly one for this category/supertype. Skipped entirely in
  // edit mode, where media_subtype_id is already set from the item.
  useEffect(() => {
    if (form.media_subtype_id) return
    const opts = mediaSubtypes.filter((s) => s.category === category && s.supertype === supertype)
    if (opts.length === 0) return

    const candidateKeys = [`${category}:${supertype}:${candidate?.media_kind}`, `${category}:${supertype}`]
    for (const key of candidateKeys) {
      const guessName = AUTO_SUBTYPE_NAME[key]
      const match = guessName && opts.find((s) => s.name.toLowerCase() === guessName.toLowerCase())
      if (match) {
        set('media_subtype_id', String(match.id))
        return
      }
    }

    if (opts.length === 1) set('media_subtype_id', String(opts[0].id))
  }, [mediaSubtypes, category, supertype]) // eslint-disable-line react-hooks/exhaustive-deps

  const handlePlatformChange = (value) => {
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
      invalidate()
      await ensureLoaded()
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
        igdb_id: form.igdb_id ? Number(form.igdb_id) : null,
        musicbrainz_id: form.musicbrainz_id || null,
        openlibrary_id: form.openlibrary_id || null,
        location_id: supertype === 'physical' && form.location_id ? Number(form.location_id) : null,
        platform_id: supertype === 'digital' && form.platform_id ? Number(form.platform_id) : null,
      }
      const saved = isEdit
        ? await mediaApi.update(item.id, payload)
        : await mediaApi.create(payload)
      toast.success(isEdit ? `"${saved.title}" updated` : `"${saved.title}" added to your collection!`)
      onSaved(saved)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const previewSrc = (isEdit && (item.cover_url || item.cover_thumb_url)) || form.cover_image_url

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {isEdit ? 'Edit item' : 'Confirm details'}
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {isEdit ? 'Update the details below' : 'Review and edit before saving'}
        </p>
      </div>

      {/* Cover preview */}
      {previewSrc && (
        <div className="flex justify-center">
          <img
            src={coverProxyUrl(previewSrc)}
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

        {category === 'games' && <>
          <Input label="Developer" value={form.developer} onChange={(e) => set('developer', e.target.value)} className="sm:col-span-2" />
        </>}

        <Input label="Genre(s)" value={form.genres} onChange={(e) => set('genres', e.target.value)} placeholder="e.g. Rock, Alternative" />
        <Input label="Edition" value={form.edition} onChange={(e) => set('edition', e.target.value)} placeholder="e.g. Special Edition, 4K UHD" />

        <ListsMultiSelect category={category} value={form.list_ids} onChange={(ids) => set('list_ids', ids)} className="sm:col-span-2" />

        <Input label="Barcode" value={form.barcode} onChange={(e) => set('barcode', e.target.value)} />

        {supertype === 'physical' && (
          <LocationPicker
            label="Location"
            locations={locations}
            value={form.location_id}
            onChange={(value) => set('location_id', value)}
          />
        )}

        {supertype === 'digital' && (
          <div className="flex flex-col gap-1">
            <SelectMenu
              label="Platform"
              groups={[{ options: [
                { value: '', label: 'No platform' },
                ...platforms.map((p) => ({ value: String(p.id), label: p.name, platform: p })),
                { value: NEW_PLATFORM, label: '+ Add new platform…' },
              ] }]}
              value={form.platform_id}
              onChange={handlePlatformChange}
              renderIcon={(opt) => opt.platform && <PlatformLogo platform={opt.platform} className="h-5 w-5" />}
            />
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
        <Button variant="secondary" onClick={isEdit ? onCancel : onBack} className="flex-1">
          {isEdit ? 'Cancel' : 'Back'}
        </Button>
        <Button onClick={handleSave} loading={saving} className="flex-1">
          {isEdit ? 'Save changes' : 'Save to collection'}
        </Button>
      </div>
    </div>
  )
}
