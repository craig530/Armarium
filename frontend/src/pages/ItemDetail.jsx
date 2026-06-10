import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil, Trash2, MapPin, Upload, Check, X } from 'lucide-react'
import { mediaApi } from '../api/media'
import { locationsApi } from '../api/locations'
import { MediaTypeBadge } from '../components/ui/Badge'
import Input, { Textarea, Select } from '../components/ui/Input'
import Button from '../components/ui/Button'
import { PageLoader } from '../components/ui/LoadingSpinner'
import toast from 'react-hot-toast'

const MEDIA_TYPES = [
  { value: 'cd', label: 'CD' },
  { value: 'dvd', label: 'DVD' },
  { value: 'bluray', label: 'Blu-ray' },
  { value: 'book', label: 'Book' },
]

export default function ItemDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const fileRef = useRef()

  const [item, setItem] = useState(null)
  const [locations, setLocations] = useState([])
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([mediaApi.get(id), locationsApi.list()])
      .then(([item, locs]) => {
        setItem(item)
        setForm(item)
        setLocations(locs)
      })
      .catch(() => toast.error('Failed to load item'))
      .finally(() => setLoading(false))
  }, [id])

  const flatLocations = []
  const flatten = (locs, depth = 0) => {
    for (const loc of locs) {
      flatLocations.push({ ...loc, depth })
      if (loc.children?.length) flatten(loc.children, depth + 1)
    }
  }
  flatten(locations)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await mediaApi.update(id, form)
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
    if (!confirm(`Delete "${item.title}"?`)) return
    await mediaApi.delete(id)
    toast.success('Deleted')
    navigate('/library')
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

  if (loading) return <PageLoader />
  if (!item) return <div className="text-center py-20 text-gray-400">Item not found</div>

  const type = editing ? form.media_type : item.media_type
  const creator = item.artist || item.director || item.author

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
            <img src={item.cover_url} alt={item.title} className="w-full aspect-[2/3] object-cover" onError={(e) => { e.target.style.display='none' }} />
          ) : (
            <div className="w-full aspect-[2/3] flex items-center justify-center text-5xl">
              {item.media_type === 'book' ? '📚' : item.media_type === 'cd' ? '💿' : '📀'}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0 space-y-2">
          {editing ? (
            <Input value={form.title} onChange={(e) => set('title', e.target.value)} className="text-lg font-bold" />
          ) : (
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{item.title}</h1>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <MediaTypeBadge type={item.media_type} />
            {item.year && <span className="text-sm text-gray-500">{item.year}</span>}
            {item.edition && <span className="text-sm px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{item.edition}</span>}
          </div>
          {creator && <p className="text-gray-600 dark:text-gray-300">{creator}</p>}
          {item.location_path && (
            <div className="flex items-center gap-1 text-sm text-gray-500">
              <MapPin size={13} />
              {item.location_path}
            </div>
          )}
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

      {/* Edit form / Detail fields */}
      {editing ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <Select label="Type" value={form.media_type} onChange={(e) => set('media_type', e.target.value)}>
            {MEDIA_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </Select>
          <Input label="Year" type="number" value={form.year || ''} onChange={(e) => set('year', e.target.value)} />
          <Input label="Genre(s)" value={form.genres || ''} onChange={(e) => set('genres', e.target.value)} />
          <Input label="Edition" value={form.edition || ''} onChange={(e) => set('edition', e.target.value)} />

          {(type === 'cd') && <>
            <Input label="Artist" value={form.artist || ''} onChange={(e) => set('artist', e.target.value)} />
            <Input label="Label" value={form.label || ''} onChange={(e) => set('label', e.target.value)} />
            <Input label="Track count" type="number" value={form.track_count || ''} onChange={(e) => set('track_count', e.target.value)} />
          </>}
          {(type === 'dvd' || type === 'bluray') && <>
            <Input label="Director" value={form.director || ''} onChange={(e) => set('director', e.target.value)} />
            <Input label="Studio" value={form.studio || ''} onChange={(e) => set('studio', e.target.value)} />
            <Input label="Runtime (mins)" type="number" value={form.runtime_minutes || ''} onChange={(e) => set('runtime_minutes', e.target.value)} />
            <Input label="Rating" value={form.rating || ''} onChange={(e) => set('rating', e.target.value)} />
          </>}
          {type === 'book' && <>
            <Input label="Author" value={form.author || ''} onChange={(e) => set('author', e.target.value)} />
            <Input label="Publisher" value={form.publisher || ''} onChange={(e) => set('publisher', e.target.value)} />
            <Input label="ISBN" value={form.isbn || ''} onChange={(e) => set('isbn', e.target.value)} />
            <Input label="Pages" type="number" value={form.page_count || ''} onChange={(e) => set('page_count', e.target.value)} />
          </>}

          <Select label="Location" value={form.location_id || ''} onChange={(e) => set('location_id', e.target.value || null)}>
            <option value="">No location</option>
            {flatLocations.map((loc) => (
              <option key={loc.id} value={loc.id}>{'  '.repeat(loc.depth)}{loc.name}</option>
            ))}
          </Select>
          <Input label="Barcode" value={form.barcode || ''} onChange={(e) => set('barcode', e.target.value)} />
          <Input label="Cover URL" value={form.cover_image_url || ''} onChange={(e) => set('cover_image_url', e.target.value)} className="col-span-2" />
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
                ['Type', item.media_type?.toUpperCase()],
                ['Year', item.year],
                ['Edition', item.edition],
                ['Artist', item.artist],
                ['Label', item.label],
                ['Tracks', item.track_count],
                ['Director', item.director],
                ['Studio', item.studio],
                ['Runtime', item.runtime_minutes && `${item.runtime_minutes} min`],
                ['Rating', item.rating],
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
          </div>

          {item.notes && (
            <div className="rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Notes</h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">{item.notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
