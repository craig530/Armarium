import { useEffect, useRef, useState } from 'react'
import { BrowserMultiFormatReader } from '@zxing/library'
import { X, Camera, CameraOff } from 'lucide-react'
import Button from '../ui/Button'

export default function BarcodeScanner({ onDetected, onClose }) {
  const videoRef = useRef(null)
  const readerRef = useRef(null)
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [error, setError] = useState(null)
  const [scanning, setScanning] = useState(false)

  useEffect(() => {
    const reader = new BrowserMultiFormatReader()
    readerRef.current = reader

    reader.listVideoInputDevices().then((videoDevices) => {
      setDevices(videoDevices)
      // Prefer rear camera on mobile
      const rear = videoDevices.find(
        (d) => /back|rear|environment/i.test(d.label)
      )
      setSelectedDevice((rear || videoDevices[0])?.deviceId || null)
    }).catch(() => setError('Camera access denied or unavailable.'))

    return () => {
      reader.reset()
    }
  }, [])

  useEffect(() => {
    if (!selectedDevice || !videoRef.current) return

    const reader = readerRef.current
    setScanning(true)
    setError(null)

    reader
      .decodeFromVideoDevice(selectedDevice, videoRef.current, (result, err) => {
        if (result) {
          const text = result.getText()
          reader.reset()
          setScanning(false)
          onDetected(text)
        }
        if (err && err.name !== 'NotFoundException') {
          setError('Scanner error: ' + err.message)
        }
      })
      .catch((e) => {
        setError(e.message || 'Could not start camera.')
        setScanning(false)
      })

    return () => {
      reader.reset()
    }
  }, [selectedDevice]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-4">
      {/* Camera selector */}
      {devices.length > 1 && (
        <select
          value={selectedDevice || ''}
          onChange={(e) => {
            readerRef.current?.reset()
            setSelectedDevice(e.target.value)
          }}
          className="w-full rounded-lg border px-3 py-2 text-sm bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white"
        >
          {devices.map((d) => (
            <option key={d.deviceId} value={d.deviceId}>
              {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
            </option>
          ))}
        </select>
      )}

      {/* Video viewport */}
      <div className="relative overflow-hidden rounded-xl bg-black aspect-video w-full">
        <video ref={videoRef} className="w-full h-full object-cover" />

        {/* Aim overlay */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-48 h-32">
            {/* Corner brackets */}
            {[
              'top-0 left-0 border-t-4 border-l-4 rounded-tl-lg',
              'top-0 right-0 border-t-4 border-r-4 rounded-tr-lg',
              'bottom-0 left-0 border-b-4 border-l-4 rounded-bl-lg',
              'bottom-0 right-0 border-b-4 border-r-4 rounded-br-lg',
            ].map((cls, i) => (
              <span key={i} className={`absolute w-6 h-6 border-white/80 ${cls}`} />
            ))}
            {/* Scan line */}
            {scanning && (
              <div className="absolute left-2 right-2 h-0.5 bg-brand-400/80 top-1/2 animate-bounce" />
            )}
          </div>
        </div>

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/70">
            <div className="text-center p-4">
              <CameraOff className="mx-auto mb-2 text-red-400" size={32} />
              <p className="text-white text-sm">{error}</p>
            </div>
          </div>
        )}
      </div>

      <p className="text-sm text-center text-gray-500 dark:text-gray-400">
        Point your camera at a barcode
      </p>

      <Button variant="outline" onClick={onClose}>
        Cancel scanning
      </Button>
    </div>
  )
}
