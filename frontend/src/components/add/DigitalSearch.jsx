import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import Button from '../ui/Button'
import Input from '../ui/Input'
import { lookupApi } from '../../api/lookup'
import toast from 'react-hot-toast'

const SEARCH_PLACEHOLDERS = {
  music: 'Search by album or artist…',
  films_tv: 'Search by title…',
  books: 'Search by title or author…',
}

const MEDIA_KINDS = [
  { value: 'movie', label: 'Film' },
  { value: 'tv', label: 'TV' },
]

// Digital items have no barcode to scan, so this is a text-search-only
// counterpart to ScanOrSearch (which remains physical-only). Films & TV adds
// a Film/TV toggle that's passed through to TMDB as `media_kind` so results
// don't mix movies and TV shows together.
export default function DigitalSearch({ category, onResults, query, onQueryChange, mediaKind, onMediaKindChange }) {
  const setQuery = onQueryChange
  const setMediaKind = onMediaKindChange
  const [loading, setLoading] = useState(false)

  const doSearch = async (q) => {
    if (!q.trim()) return
    setLoading(true)
    try {
      const results = await lookupApi.search(q, category, 10, category === 'films_tv' ? mediaKind : null)
      if (!results.length) {
        toast('No results found — try a different search term.', { icon: '🔍' })
      }
      onResults(results)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Add to your collection</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Search by title</p>
      </div>

      {category === 'films_tv' && (
        <div className="inline-flex self-start rounded-lg border border-gray-200 dark:border-gray-700 p-0.5">
          {MEDIA_KINDS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setMediaKind(opt.value)}
              className={clsx(
                'px-3 py-1.5 text-sm rounded-md font-medium transition-colors',
                mediaKind === opt.value
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); doSearch(query) }} className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={SEARCH_PLACEHOLDERS[category]}
          className="flex-1"
          autoFocus
        />
        <Button type="submit" loading={loading} size="icon">
          {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
        </Button>
      </form>

      <p className="text-xs text-gray-400 text-center">
        Books use OpenLibrary · Music uses MusicBrainz · Films & TV use TMDB (requires API key)
      </p>
    </div>
  )
}
