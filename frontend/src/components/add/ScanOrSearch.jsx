import { useState } from 'react'
import { Scan, Search, Loader2 } from 'lucide-react'
import Button from '../ui/Button'
import Input, { Select } from '../ui/Input'
import BarcodeScanner from '../scanner/BarcodeScanner'
import { lookupApi } from '../../api/lookup'
import toast from 'react-hot-toast'

const TYPES = [
  { value: 'cd', label: 'CD / Music' },
  { value: 'dvd', label: 'DVD' },
  { value: 'bluray', label: 'Blu-ray' },
  { value: 'book', label: 'Book' },
]

export default function ScanOrSearch({ onResults }) {
  const [mode, setMode] = useState('search')   // 'search' | 'scan'
  const [query, setQuery] = useState('')
  const [manualBarcode, setManualBarcode] = useState('')
  const [mediaType, setMediaType] = useState('book')
  const [loading, setLoading] = useState(false)

  const doSearch = async (q, type) => {
    if (!q.trim()) return
    setLoading(true)
    try {
      const results = await lookupApi.search(q, type)
      if (!results.length) {
        toast('No results found — try a different search term.', { icon: '🔍' })
      }
      onResults(results, type)
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
      const results = await lookupApi.barcode(barcode, mediaType)
      if (!results.length) {
        toast('No barcode match found — try a title search.', { icon: '📋' })
        setQuery(barcode)
      }
      onResults(results, mediaType)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleManualBarcodeSubmit = (e) => {
    e.preventDefault()
    const code = manualBarcode.trim()
    if (!code) return
    handleBarcodeDetected(code)
    setManualBarcode('')
  }

  if (mode === 'scan') {
    return <BarcodeScanner onDetected={handleBarcodeDetected} onClose={() => setMode('search')} />
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Add to your collection</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Scan a barcode or search by title</p>
      </div>

      {/* Media type selector */}
      <div className="grid grid-cols-4 gap-2">
        {TYPES.map((t) => (
          <button
            key={t.value}
            onClick={() => setMediaType(t.value)}
            className={`py-2 rounded-lg text-sm font-medium transition-colors ${
              mediaType === t.value
                ? 'bg-brand-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Search input */}
      <form
        onSubmit={(e) => { e.preventDefault(); doSearch(query, mediaType) }}
        className="flex gap-2"
      >
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            mediaType === 'book' ? 'Search by title or author…'
            : mediaType === 'cd' ? 'Search by album or artist…'
            : 'Search by film or TV title…'
          }
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
        Books use OpenLibrary · CDs use MusicBrainz · Films use TMDB (requires API key)
      </p>
    </div>
  )
}
