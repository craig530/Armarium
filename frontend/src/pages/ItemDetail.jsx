import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil, Trash2, Upload, Check, X, Link2, Unlink, RefreshCw } from 'lucide-react'
import { mediaApi } from '../api/media'
import { useReferenceDataStore } from '../store'
import { MediaSubtypeIcon, OwnershipIcon } from '../components/ui/Badge'
import { OWNERSHIP_ICONS } from '../lib/mediaIcons'
import CoverImage from '../components/media/CoverImage'
import LocationIcon from '../components/ui/LocationIcon'
import PlatformLogo from '../components/ui/PlatformLogo'
import Input, { Textarea, Select } from '../components/ui/Input'
import SelectMenu from '../components/ui/SelectMenu'
import LocationPicker from '../components/locations/LocationPicker'
import Button from '../components/ui/Button'
import { PageLoader } from '../components/ui/LoadingSpinner'
import TMDBAttribution from '../components/ui/TMDBAttribution'
import { CATEGORIES, categoryLabel, supertypeLabel } from '../lib/categories'
import { useConfirm } from '../hooks/useConfirm'
import toast from 'react-hot-toast'

function OwnershipEntry({ children, action }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 min-w-0">{children}</div>
      {action}
    </div>
  )
}

// Uniform 40px icon slot for an ownership row — a location icon or platform
// logo, with a small physical/digital glyph badged in the corner.
function OwnershipIconSlot({ supertype, location, platform }) {
  const Glyph = OWNERSHIP_ICONS[supertype]
  return (
    <div className="relative shrink-0">
      {supertype === 'physical' ? (
        <div className="h-10 w-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <LocationIcon location={location} size={20} className="text-gray-400 dark:text-gray-500" />
        </div>
      ) : (
        <PlatformLogo platform={platform} className="h-10 w-10" />
      )}
      {Glyph && (
        <span className="absolute -bottom-1 -right-1 flex items-center justify-center h-4 w-4 rounded-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
          <Glyph size={10} />
        </span>
      )}
    </div>
  )
}

function LinkSearch({ item, onLinked, onCancel }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [linking, setLinking] = useState(false)
  const oppositeSupertype = item.supertype === 'physical' ? 'digital' : 'physical'

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    setSearching(true)
    const handle = setTimeout(() => {
      mediaApi.list({ category: item.category, supertype: oppositeSupertype, q: query, per_page: 10 })
        .then((r) => setResults(r.items.filter((i) => i.id !== item.id)))
        .catch(() => {})
        .finally(() => setSearching(false))
    }, 300)
    return () => clearTimeout(handle)
  }, [query, item.id, item.category, oppositeSupertype])

  const handleLink = async (candidate) => {
    setLinking(true)
    try {
      await mediaApi.link(item.id, candidate.id)
      toast.success(`Linked to "${candidate.title}"`)
      onLinked()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLinking(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`Search your ${categoryLabel(item.category).toLowerCase()} ${oppositeSupertype} items…`}
          className="flex-1"
          autoFocus
        />
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
      </div>
      {searching && <p className="text-xs text-gray-400">Searching…</p>}
      {!searching && query.trim() && results.length === 0 && (
        <p className="text-xs text-gray-400">No matching {oppositeSupertype} items found</p>
      )}
      {results.length > 0 && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => handleLink(r)}
              disabled={linking}
              className="w-full flex items-center justify-between gap-2 p-2 rounded-lg text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              <span className="truncate">{r.title}{r.year ? ` (${r.year})` : ''}</span>
              <MediaSubtypeIcon subtype={r.media_subtype} className="shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ItemDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const fileRef = useRef()

  const { locations, platforms, mediaSubtypes, ensureLoaded } = useReferenceDataStore()
  const [item, setItem] = useState(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showLinkSearch, setShowLinkSearch] = useState(false)
  const [refreshingCover, setRefreshingCover] = useState(false)
  const [confirm, confirmDialog] = useConfirm()

  const load = () => {
    return mediaApi.get(id).then((updated) => {
      setItem(updated)
      setForm(updated)
      return updated
    })
  }

  useEffect(() => {
    ensureLoaded()
    mediaApi.get(id)
      .then((item) => {
        setItem(item)
        setForm(item)
      })
      .catch(() => toast.error('Failed to load item'))
      .finally(() => setLoading(false))
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const subtypeOptions = item
    ? mediaSubtypes
        .filter((s) => s.category === item.category && s.supertype === item.supertype)
        .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
    : []

  const handleSave = async () => {
    if (!form.title?.trim()) return toast.error('Title is required')
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
        location_id: form.location_id ? Number(form.location_id) : null,
        platform_id: form.platform_id ? Number(form.platform_id) : null,
      }
      const updated = await mediaApi.update(id, payload)
      setItem(updated)
      setForm(updated)
      setEditing(false)
      toast.success('Saved')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!await confirm(`Delete "${item.title}"?`)) return
    await mediaApi.delete(id)
    toast.success('Deleted')
    const slug = CATEGORIES.find((c) => c.value === item.category)?.slug
    navigate(`/library/${slug}`)
  }

  const handleCoverUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const updated = await mediaApi.uploadCover(id, file)
      setItem(updated)
      setForm(updated)
      toast.success('Cover updated')
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleRefreshCover = async () => {
    setRefreshingCover(true)
    try {
      const updated = await mediaApi.refreshCover(id)
      setItem(updated)
      setForm(updated)
      toast.success('Cover refreshed')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setRefreshingCover(false)
    }
  }

  const handleUnlink = async () => {
    if (!await confirm('Unlink these items?')) return
    try {
      await mediaApi.unlink(id)
      await load()
      toast.success('Unlinked')
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleLinked = async () => {
    await load()
    setShowLinkSearch(false)
  }

  if (loading) return <PageLoader />
  if (!item) return <div className="text-center py-20 text-gray-400">Item not found</div>

  const creator = item.artist || item.director || item.author
  const linked = item.linked_item

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Back + actions */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft size={18} />
        </Button>
        <div className="flex-1" />
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleCoverUpload} />
        <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
          <Upload size={14} /> Cover
        </Button>
        {!editing && (
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            <Pencil size={14} /> Edit
          </Button>
        )}
        {editing && (
          <>
            <Button size="sm" loading={saving} onClick={handleSave}>
              <Check size={14} /> Save
            </Button>
            <Button variant="ghost" size="sm" onClick={() => { setEditing(false); setForm(item) }}>
              <X size={14} /> Cancel
            </Button>
          </>
        )}
        <Button variant="danger" size="icon" onClick={handleDelete}>
          <Trash2 size={16} />
        </Button>
      </div>

      {/* Hero */}
      <div className="flex gap-6 items-start">
        <div className="shrink-0 w-36 rounded-xl overflow-hidden shadow-lg bg-gray-100 dark:bg-gray-800">
          {item.cover_url ? (
            <img src={item.cover_url} alt={item.title} className="w-full aspect-[2/3] object-cover" onError={(e) => { e.target.style.display = 'none' }} />
          ) : (
            <CoverImage category={item.category} title={item.title} size="full" className="aspect-[2/3]" />
          )}
        </div>

        <div className="flex-1 min-w-0 space-y-2">
          {editing ? (
            <Input value={form.title} onChange={(e) => set('title', e.target.value)} className="text-lg font-bold" />
          ) : (
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{item.title}</h1>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <MediaSubtypeIcon subtype={item.media_subtype} />
            <OwnershipIcon ownership={item.ownership} />
            {item.year && <span className="text-sm text-gray-500">{item.year}</span>}
            {item.edition && <span className="text-sm px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{item.edition}</span>}
          </div>
          {creator && <p className="text-gray-600 dark:text-gray-300">{creator}</p>}
          {item.genres && (
            <div className="flex flex-wrap gap-1">
              {item.genres.split(',').map((g) => (
                <span key={g} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                  {g.trim()}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Ownership */}
      <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Ownership</h3>

        <OwnershipEntry>
          <OwnershipIconSlot
            supertype={item.supertype}
            location={{ icon_key: item.location_icon_key, icon_url: item.location_icon_url }}
            platform={item.platform}
          />
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {item.supertype === 'physical' ? (item.location_path || 'No location') : (item.platform?.name || 'No platform')}
            </p>
            <p className="text-xs text-gray-400">{supertypeLabel(item.supertype)} · {item.media_subtype?.name}</p>
          </div>
        </OwnershipEntry>

        <div className="pt-3 border-t border-gray-100 dark:border-gray-800">
          {linked ? (
            <OwnershipEntry
              action={
                <Button variant="ghost" size="sm" onClick={handleUnlink}>
                  <Unlink size={14} /> Unlink
                </Button>
              }
            >
              <button onClick={() => navigate(`/item/${linked.id}`)} className="flex items-center gap-3 min-w-0 text-left hover:opacity-80">
                <OwnershipIconSlot
                  supertype={linked.supertype}
                  location={{ icon_key: linked.location_icon_key, icon_url: linked.location_icon_url }}
                  platform={linked.platform}
                />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{linked.title}</p>
                  <p className="text-xs text-gray-400 truncate">
                    {supertypeLabel(linked.supertype)} · {linked.media_subtype?.name} · {linked.supertype === 'physical' ? (linked.location_path || 'No location') : (linked.platform?.name || 'No platform')}
                  </p>
                </div>
              </button>
            </OwnershipEntry>
          ) : showLinkSearch ? (
            <LinkSearch item={item} onLinked={handleLinked} onCancel={() => setShowLinkSearch(false)} />
          ) : (
            <Button variant="outline" size="sm" onClick={() => setShowLinkSearch(true)}>
              <Link2 size={14} /> Link {item.supertype === 'physical' ? 'digital' : 'physical'} copy
            </Button>
          )}
        </div>
      </div>

      {/* Edit form / Detail fields */}
      {editing ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <Select label="Type" value={form.media_subtype_id || ''} onChange={(e) => set('media_subtype_id', e.target.value)}>
            {subtypeOptions.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
          <Input label="Year" type="number" value={form.year || ''} onChange={(e) => set('year', e.target.value)} />
          <Input label="Genre(s)" value={form.genres || ''} onChange={(e) => set('genres', e.target.value)} />
          <Input label="Edition" value={form.edition || ''} onChange={(e) => set('edition', e.target.value)} />

          {item.category === 'music' && <>
            <Input label="Artist" value={form.artist || ''} onChange={(e) => set('artist', e.target.value)} />
            <Input label="Label" value={form.label || ''} onChange={(e) => set('label', e.target.value)} />
            <Input label="Track count" type="number" value={form.track_count || ''} onChange={(e) => set('track_count', e.target.value)} />
          </>}
          {item.category === 'films_tv' && <>
            <Input label="Director" value={form.director || ''} onChange={(e) => set('director', e.target.value)} />
            <Input label="Studio" value={form.studio || ''} onChange={(e) => set('studio', e.target.value)} />
            <Input label="Runtime (mins)" type="number" value={form.runtime_minutes || ''} onChange={(e) => set('runtime_minutes', e.target.value)} />
            <Input label="Rating" value={form.rating || ''} onChange={(e) => set('rating', e.target.value)} />
            <Input label="Seasons owned" value={form.seasons_owned || ''} onChange={(e) => set('seasons_owned', e.target.value)} />
            <Input label="Episode count" type="number" value={form.episode_count || ''} onChange={(e) => set('episode_count', e.target.value)} />
          </>}
          {item.category === 'books' && <>
            <Input label="Author" value={form.author || ''} onChange={(e) => set('author', e.target.value)} />
            <Input label="Publisher" value={form.publisher || ''} onChange={(e) => set('publisher', e.target.value)} />
            <Input label="ISBN" value={form.isbn || ''} onChange={(e) => set('isbn', e.target.value)} />
            <Input label="Pages" type="number" value={form.page_count || ''} onChange={(e) => set('page_count', e.target.value)} />
          </>}

          {item.supertype === 'physical' ? (
            <LocationPicker
              label="Location"
              locations={locations}
              value={form.location_id || ''}
              onChange={(value) => set('location_id', value)}
            />
          ) : (
            <SelectMenu
              label="Platform"
              groups={[{ options: [
                { value: '', label: 'No platform' },
                ...platforms.map((p) => ({ value: String(p.id), label: p.name, platform: p })),
              ] }]}
              value={form.platform_id || ''}
              onChange={(value) => set('platform_id', value)}
              renderIcon={(opt) => opt.platform && <PlatformLogo platform={opt.platform} className="h-5 w-5" />}
            />
          )}

          <Input label="Barcode" value={form.barcode || ''} onChange={(e) => set('barcode', e.target.value)} />
          <div className="col-span-2">
            <div className="flex items-end gap-2">
              <Input label="Cover URL" value={form.cover_image_url || ''} onChange={(e) => set('cover_image_url', e.target.value)} className="flex-1" />
              {item.cover_image_url && (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  title="Redownload cover from URL"
                  loading={refreshingCover}
                  onClick={handleRefreshCover}
                >
                  <RefreshCw size={14} />
                </Button>
              )}
            </div>
            <p className="mt-1 text-xs text-gray-400">Uploading a photo replaces this URL.</p>
          </div>
          <Textarea label="Description" value={form.description || ''} onChange={(e) => set('description', e.target.value)} rows={3} className="col-span-2" />
          <Textarea label="Notes" value={form.notes || ''} onChange={(e) => set('notes', e.target.value)} rows={2} className="col-span-2" />
        </div>
      ) : (
        <div className="space-y-4">
          {item.description && (
            <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Description</h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">{item.description}</p>
            </div>
          )}

          <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">Details</h3>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
              {[
                ['Type', item.media_subtype?.name],
                ['Year', item.year],
                ['Edition', item.edition],
                ['Artist', item.artist],
                ['Label', item.label],
                ['Tracks', item.track_count],
                ['Director', item.director],
                ['Studio', item.studio],
                ['Runtime', item.runtime_minutes && `${item.runtime_minutes} min`],
                ['Rating', item.rating],
                ['Seasons', item.seasons_owned],
                ['Episodes', item.episode_count],
                ['Author', item.author],
                ['Publisher', item.publisher],
                ['ISBN', item.isbn],
                ['Pages', item.page_count],
                ['Language', item.language],
                ['Barcode', item.barcode],
              ]
                .filter(([, v]) => v)
                .map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs text-gray-400">{label}</dt>
                    <dd className="text-sm font-medium text-gray-900 dark:text-white">{value}</dd>
                  </div>
                ))}
            </dl>
            {item.category === 'films_tv' && <TMDBAttribution className="mt-3" />}
          </div>

          {item.notes && (
            <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Notes</h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">{item.notes}</p>
            </div>
          )}
        </div>
      )}

      {confirmDialog}
    </div>
  )
}
