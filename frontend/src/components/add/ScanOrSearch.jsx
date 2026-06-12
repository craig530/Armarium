import { lazy, Suspense, useState } from 'react'
import { Scan, Search, Loader2 } from 'lucide-react'
import Button from '../ui/Button'
import Input from '../ui/Input'
import LoadingSpinner from '../ui/LoadingSpinner'
import { lookupApi } from '../../api/lookup'
import toast from 'react-hot-toast'

// The barcode scanner pulls in @zxing/library (~400KB) — only fetch it once
// the user actually opts to scan, rather than on every Add Item page load.
const BarcodeScanner = lazy(() => import('../scanner/BarcodeScanner'))

const SEARCH_PLACEHOLDERS = {
  music: 'Search by album or artist…',
  films_tv: 'Search by film or TV title…',
  books: 'Search by title or author…',
}

export default function ScanOrSearch({ category, onResults }) {
  const [mode, setMode] = useState('search')   // 'search' | 'scan'
  const [query, setQuery] = useState('')
  const [manualBarcode, setManualBarcode] = useState('')
  const [loading, setLoading] = useState(false)

  const doSearch = async (q) => {
    if (!q.trim()) return
    setLoading(true)
    try {
      const results = await lookupApi.search(q, category)
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

  const handleBarcodeDetected = async (barcode) => {
    setMode('search')
    setLoading(true)
    toast.success(`Barcode detected: ${barcode}`)
    try {
      const results = await lookupApi.barcode(barcode, category)
      if (!results.length) {
        toast('No barcode match found — try a title search.', { icon: '📋' })
        setQuery(barcode)
      } else {
        const count = results[0]?.metadata?.library_count || 0
        if (count > 0) {
          toast(`You already have ${count} ${count === 1 ? 'copy' : 'copies'} of this in your library.`, { icon: '📚' })
        }
      }
      onResults(results)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleManualBarcodeSubmit = (e) => {
    e.preventDefault()
    if (!manualBarcode.trim()) return
    // Pass the raw input through untouched — all cleanup/validation
    // (whitespace, hyphens, ISBN/UPC/EAN normalisation) happens server side.
    handleBarcodeDetected(manualBarcode)
    setManualBarcode('')
  }

  if (mode === 'scan') {
    return (
      <Suspense fallback={<LoadingSpinner size="lg" className="py-12" />}>
        <BarcodeScanner onDetected={handleBarcodeDetected} onClose={() => setMode('search')} />
      </Suspense>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Add to your collection</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Scan a barcode or search by title</p>
      </div>

      {/* Search input */}
      <form
        onSubmit={(e) => { e.preventDefault(); doSearch(query) }}
        className="flex gap-2"
      >
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={SEARCH_PLACEHOLDERS[category]}
          className="flex-1"
        />
        <Button type="submit" loading={loading} size="icon">
          {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
        </Button>
      </form>

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

      {/* Manual fallback for when the camera isn't available (e.g. no HTTPS,
          camera permission denied, or no camera on the device) */}
      <form onSubmit={handleManualBarcodeSubmit} className="flex gap-2">
        <Input
          value={manualBarcode}
          onChange={(e) => setManualBarcode(e.target.value)}
          inputMode="numeric"
          placeholder="Or type the barcode/ISBN number…"
          className="flex-1"
        />
        <Button type="submit" variant="outline" loading={loading}>
          Look up
        </Button>
      </form>

      <p className="text-xs text-gray-400 text-center">
        Books use OpenLibrary · Music uses MusicBrainz · Films & TV use TMDB (requires API key)
      </p>
    </div>
  )
}
