import { lazy, Suspense, useState } from 'react'
import { Scan, Search, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import Button from '../ui/Button'
import Input from '../ui/Input'
import LoadingSpinner from '../ui/LoadingSpinner'
import { lookupApi } from '../../api/lookup'
import toast from 'react-hot-toast'

// Code-split the scanner — only fetch it once the user actually opts to
// scan, rather than on every Add Item page load.
const BarcodeScanner = lazy(() => import('../scanner/BarcodeScanner'))

const SEARCH_PLACEHOLDERS = {
  music: 'Search by album or artist, or enter a barcode…',
  films_tv: 'Search by film or TV title, or enter a barcode…',
  books: 'Search by title or author, or enter an ISBN…',
  games: 'Search by game title, or scan/enter a barcode…',
}

const MEDIA_KINDS = [
  { value: 'movie', label: 'Film' },
  { value: 'tv', label: 'TV' },
]

// A barcode/ISBN is digits only (ISBN-10 may carry a trailing "X" check
// digit), at one of the lengths real barcodes/ISBNs use — anything else is
// treated as a title/artist/author search. Deliberately more permissive than
// `BarcodeScanner.jsx`'s `looksLikeRecognizedBarcode` (which also validates
// the check digit): this only decides which lookup endpoint to call, and the
// backend rejects anything it can't actually process.
function looksLikeBarcode(value) {
  const cleaned = value.trim().replace(/[\s-]/g, '')
  if (!/^\d+[Xx]?$/.test(cleaned)) return false
  return [8, 10, 12, 13, 18].includes(cleaned.length)
}

export default function ScanOrSearch({ category, onResults, batchMode, query, onQueryChange, mediaKind, onMediaKindChange }) {
  // In batch mode, default straight to the camera — that's the whole point
  // of rapid scanning — and each fresh mount (after a save returns here)
  // starts scanning again automatically.
  const [mode, setMode] = useState(batchMode ? 'scan' : 'search')   // 'search' | 'scan'
  const setQuery = onQueryChange
  const setMediaKind = onMediaKindChange
  const [loading, setLoading] = useState(false)
  // Bumped to tell BarcodeScanner to resume scanning without remounting, when
  // a detected code is a miss/error and batch mode is staying on this screen.
  const [restartSignal, setRestartSignal] = useState(0)

  const doSearch = async (q) => {
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

  const doBarcodeLookup = async (barcode) => {
    setLoading(true)
    try {
      const results = await lookupApi.barcode(barcode, category)
      if (!results.length) {
        // Stay on the scan screen and keep scanning — the barcode is
        // pre-filled into the combined field so a manual exit to search still
        // has it ready to try as a title search.
        toast('No barcode match found — try a title search.', { icon: '📋' })
        setQuery(barcode)
        setRestartSignal((n) => n + 1)
      } else {
        toast.success(`Barcode detected: ${barcode}`)
        const count = results[0]?.metadata?.library_count || 0
        if (count > 0) {
          toast(`You already have ${count} ${count === 1 ? 'copy' : 'copies'} of this in your library.`, { icon: '📚' })
        }
      }
      onResults(results)
    } catch (err) {
      toast.error(err.message)
      setRestartSignal((n) => n + 1)
    } finally {
      setLoading(false)
    }
  }

  // Smart dispatch: a single field handles both "search by title" and "look
  // up by barcode/ISBN" — whichever the input looks like decides which
  // lookup endpoint gets called.
  const handleSubmit = (e) => {
    e.preventDefault()
    const value = query.trim()
    if (!value || loading) return
    if (looksLikeBarcode(value)) {
      doBarcodeLookup(value)
    } else {
      doSearch(value)
    }
  }

  // Stays available while the camera scanner is open too — it's the fallback
  // for codes the camera can't read (damaged labels, no camera permission,
  // etc.), and doubles as the title-search box so batch mode never loses the
  // ability to search by title.
  const combinedInput = (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={SEARCH_PLACEHOLDERS[category]}
        className="flex-1"
      />
      <Button type="submit" disabled={loading} size="icon">
        {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
      </Button>
    </form>
  )

  const mediaKindToggle = category === 'films_tv' && (
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
  )

  if (mode === 'scan') {
    return (
      <div className="flex flex-col gap-5">
        <Suspense fallback={<LoadingSpinner size="lg" className="py-12" />}>
          <BarcodeScanner onDetected={doBarcodeLookup} onClose={() => setMode('search')} restartSignal={restartSignal} loading={loading} />
        </Suspense>
        {mediaKindToggle}
        {combinedInput}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Add to your collection</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Search by title, scan a barcode, or type one in</p>
      </div>

      {mediaKindToggle}

      {combinedInput}

      {/* Barcode scan button */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200 dark:border-gray-700" />
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="px-3 bg-gray-50 dark:bg-gray-950 text-gray-400">or</span>
        </div>
      </div>

      <Button variant="outline" onClick={() => setMode('scan')} className="w-full">
        <Scan size={18} />
        Scan barcode with camera
      </Button>

      <p className="text-xs text-gray-400 text-center">
        Books use OpenLibrary · Music uses MusicBrainz · Films &amp; TV use TMDB · Games use IGDB (all require API keys except OpenLibrary/MusicBrainz)
      </p>
    </div>
  )
}
