import { useEffect, useRef, useState } from 'react'
import { CameraOff, Flashlight, FlashlightOff, Loader2 } from 'lucide-react'
import Button from '../ui/Button'
import { lookupApi } from '../../api/lookup'

const SECURE_CONTEXT_ERROR =
  'Camera scanning requires a secure (HTTPS) connection. Use manual entry below, or access this site over HTTPS.'

// How often to send a cropped frame to the backend for decoding. The
// `isProcessingRef` lock means the actual cadence is max(this, round-trip
// time) — this is a floor, not a guarantee.
const SCAN_INTERVAL_MS = 200

// Number of consecutive identical, checksum-valid decodes required before
// accepting a result. A single-frame misread that happens to pass the shape
// and checksum checks is extremely unlikely to repeat identically on the
// very next frame, while a real, steadily-held barcode decodes the same way
// many times in a row.
const CONFIRM_MATCHES = 2

// Minimum time between invalid-format flash/vibrate feedback for the same
// decoded text, so a held-up unsupported barcode doesn't flash every frame.
const INVALID_FLASH_COOLDOWN_MS = 1500

const GUIDANCE_TEXT = {
  default: 'Point your camera at a barcode',
  holdSteady: 'Hold steady — almost there',
}

// Mirrors the shape checks in `app/services/barcode.py::process_barcode` —
// used to decide whether a decoded result is a barcode we can actually look
// up, or just some other barcode-shaped code (e.g. a QR code or a
// foreign/garbled retail code) that should be flagged rather than accepted.
function looksLikeRecognizedBarcode(text) {
  const cleaned = (text || '').replace(/[\s-]/g, '')
  if (!/^\d+$/.test(cleaned)) return false
  const len = cleaned.length
  if ((cleaned.startsWith('978') || cleaned.startsWith('979')) && (len === 13 || len === 18)) return true
  return len === 8 || len === 12 || len === 13
}

// Validates the EAN-8/UPC-A/EAN-13 check digit (ISBN-13 uses the EAN-13
// algorithm). zxing-cpp already validates per-format checksums for EAN/UPC
// results, but a misread that happens to produce a recognised barcode
// *shape* from a different format (e.g. CODE_128 decoding to a 13-digit
// string) would skip that check — this catches those "random number" false
// positives too.
function hasValidCheckDigit(cleaned) {
  const digits = cleaned.length === 18 ? cleaned.slice(0, 13) : cleaned
  if (digits.length === 8) {
    let sum = 0
    for (let i = 0; i < 7; i++) sum += Number(digits[i]) * (i % 2 === 0 ? 3 : 1)
    return (10 - (sum % 10)) % 10 === Number(digits[7])
  }
  const ean13 = digits.length === 12 ? `0${digits}` : digits
  if (ean13.length !== 13) return true
  let sum = 0
  for (let i = 0; i < 12; i++) sum += Number(ean13[i]) * (i % 2 === 0 ? 1 : 3)
  return (10 - (sum % 10)) % 10 === Number(ean13[12])
}

function isCameraSupported() {
  return (
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    !!navigator.mediaDevices?.getUserMedia
  )
}

// Phones/tablets default to the rear-facing camera (better for barcodes);
// desktops/laptops have no "environment" camera, so default to whichever
// camera the browser picks first (typically the built-in/primary webcam).
function isMobileDevice() {
  return typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
}

function describeCameraError(err) {
  switch (err?.name) {
    case 'NotAllowedError':
    case 'PermissionDeniedError':
      return 'Camera permission was denied. Enable camera access for this site in Settings → Safari → Camera, then reopen the scanner — or use manual entry below.'
    case 'NotFoundError':
    case 'DevicesNotFoundError':
      return 'No camera was found on this device. Use manual entry below.'
    case 'NotReadableError':
    case 'TrackStartError':
      return 'The camera is already in use by another app.'
    default:
      return err?.message || 'Could not start the camera.'
  }
}

// Crops a centered horizontal band from the current video frame — wide
// enough to give margin for imprecise aiming, but small enough to keep each
// upload light. Returns a JPEG blob, or null if the video has no frame ready
// yet (e.g. dimensions not reported on the very first ticks).
function captureCroppedFrame(video, canvas) {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (!vw || !vh) return Promise.resolve(null)

  const cropW = Math.round(vw * 0.9)
  const cropH = Math.round(vh * 0.5)
  const cropX = Math.round((vw - cropW) / 2)
  const cropY = Math.round((vh - cropH) / 2)

  canvas.width = cropW
  canvas.height = cropH
  canvas.getContext('2d').drawImage(video, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH)

  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
}

export default function BarcodeScanner({ onDetected, onClose, restartSignal, loading }) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  if (!canvasRef.current && typeof document !== 'undefined') {
    canvasRef.current = document.createElement('canvas')
  }
  const streamRef = useRef(null)
  const intervalRef = useRef(null)
  const isProcessingRef = useRef(false)
  const abortRef = useRef(null)
  const lastMatchRef = useRef({ text: null, count: 0 })
  const lastInvalidRef = useRef({ text: null, time: 0 })
  const flashTimeoutRef = useRef(null)

  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  // The device actually in use, read back from the stream's track settings —
  // distinct from `selectedDevice` (the user's explicit choice, which stays
  // null until they pick one). Without this, the dropdown's `value` (null)
  // matches no <option>, so the browser falls back to showing whichever
  // device enumerates first — on iPhone that's often "Front Camera" even
  // though `facingMode: 'environment'` correctly started the rear camera.
  const [activeDeviceId, setActiveDeviceId] = useState(null)
  const [error, setError] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [guidance, setGuidance] = useState('default')
  const [flash, setFlash] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [torchOn, setTorchOn] = useState(false)

  const flashInvalid = () => {
    setFlash(true)
    navigator.vibrate?.(200)
    clearTimeout(flashTimeoutRef.current)
    flashTimeoutRef.current = setTimeout(() => setFlash(false), 400)
  }

  const stopStream = () => {
    clearInterval(intervalRef.current)
    intervalRef.current = null
    abortRef.current?.abort()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  // Applies the backend's decode results to the confirm/guidance/flash state
  // machine. A miss/unsupported-format never throws — the loop just keeps
  // polling on the next tick.
  const handleResults = (results) => {
    for (const r of results) {
      if (!looksLikeRecognizedBarcode(r.text)) continue
      const cleaned = r.text.replace(/[\s-]/g, '')
      if (!hasValidCheckDigit(cleaned)) continue

      const match = lastMatchRef.current
      lastMatchRef.current = match.text === cleaned
        ? { text: cleaned, count: match.count + 1 }
        : { text: cleaned, count: 1 }

      if (lastMatchRef.current.count >= CONFIRM_MATCHES) {
        // Pause the stream and hand off to the caller for a lookup. A
        // miss/error resumes scanning automatically via `restartSignal`.
        stopStream()
        setScanning(false)
        onDetected(r.text)
        return
      }
      setGuidance('holdSteady')
      return
    }

    lastMatchRef.current = { text: null, count: 0 }
    setGuidance('default')

    // Decoded *something* barcode-shaped, but not a format we can look up —
    // flag it rather than silently ignoring it.
    if (results.length > 0) {
      const text = results[0].text
      const now = Date.now()
      if (text !== lastInvalidRef.current.text || now - lastInvalidRef.current.time > INVALID_FLASH_COOLDOWN_MS) {
        lastInvalidRef.current = { text, time: now }
        flashInvalid()
      }
    }
  }

  const scanFrame = async () => {
    if (isProcessingRef.current) return
    const video = videoRef.current
    if (!video) return

    isProcessingRef.current = true
    try {
      const blob = await captureCroppedFrame(video, canvasRef.current)
      if (!blob) return
      const controller = new AbortController()
      abortRef.current = controller
      const data = await lookupApi.scan(blob, controller.signal)
      handleResults(data.results || [])
    } catch {
      // Network error, rate limit, or aborted request — just try again on
      // the next tick.
    } finally {
      isProcessingRef.current = false
    }
  }

  const startScanning = async () => {
    stopStream()
    setError(null)
    setFlash(false)
    setGuidance('default')
    setTorchSupported(false)
    setTorchOn(false)
    lastMatchRef.current = { text: null, count: 0 }
    lastInvalidRef.current = { text: null, time: 0 }

    // Asking for a higher resolution helps the decoder resolve small/dense
    // barcodes (e.g. paperback ISBNs) held further from the camera.
    const videoConstraints = {
      ...(selectedDevice
        ? { deviceId: { exact: selectedDevice } }
        : isMobileDevice() ? { facingMode: 'environment' } : {}),
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream

      // Device labels/ids are only populated after permission is granted —
      // re-enumerate now so the camera-switcher dropdown can show them.
      navigator.mediaDevices.enumerateDevices()
        .then((all) => setDevices(all.filter((d) => d.kind === 'videoinput')))
        .catch(() => {})

      // Record which device is actually running, for the camera-switcher
      // dropdown (see `activeDeviceId` declaration above).
      const track = stream.getVideoTracks()[0]
      setActiveDeviceId(track?.getSettings?.().deviceId || null)

      // Torch is only available on some mobile rear cameras.
      const capabilities = track?.getCapabilities?.()
      setTorchSupported(!!capabilities?.torch)

      // Some cameras (especially webcams) default to a single-shot
      // autofocus that doesn't refocus once the stream starts, which makes
      // it hard to read a barcode held close to the lens. Ask for
      // continuous autofocus where supported.
      if (capabilities?.focusMode?.includes('continuous')) {
        track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] }).catch(() => {})
      }

      setScanning(true)
      intervalRef.current = setInterval(scanFrame, SCAN_INTERVAL_MS)
    } catch (e) {
      setError(describeCameraError(e))
    }
  }

  useEffect(() => {
    if (!isCameraSupported()) {
      setError(SECURE_CONTEXT_ERROR)
      return
    }

    startScanning()

    return () => {
      stopStream()
      clearTimeout(flashTimeoutRef.current)
    }
  }, [selectedDevice]) // eslint-disable-line react-hooks/exhaustive-deps

  // Lets the caller force scanning to resume after a detected code turns out
  // to be a miss/error and the user stays on this screen — `stopStream()`
  // already stopped the camera once a code was decoded, so resuming needs an
  // explicit restart.
  useEffect(() => {
    if (!restartSignal) return
    startScanning()
  }, [restartSignal]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleTorch = async () => {
    const track = streamRef.current?.getVideoTracks?.()[0]
    if (!track) return
    try {
      await track.applyConstraints({ advanced: [{ torch: !torchOn }] })
      setTorchOn((on) => !on)
    } catch {
      // Some browsers report `torch` in getCapabilities() but reject the
      // constraint at apply time — fail silently, the button just won't toggle.
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Camera selector — populated after permission is granted */}
      {devices.length > 1 && (
        <select
          value={selectedDevice || activeDeviceId || ''}
          onChange={(e) => setSelectedDevice(e.target.value)}
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
        <video ref={videoRef} className="w-full h-full object-cover" playsInline muted autoPlay />

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
            {/* Scan line sweep */}
            {scanning && (
              <div className="absolute left-2 right-2 top-0 h-0.5 bg-brand-400/80 animate-scan-sweep" />
            )}
          </div>
        </div>

        {/* Invalid-format flash */}
        {flash && (
          <div className="absolute inset-0 bg-red-500/40 pointer-events-none transition-opacity" />
        )}

        {/* Torch toggle */}
        {scanning && torchSupported && (
          <button
            type="button"
            onClick={toggleTorch}
            aria-label={torchOn ? 'Turn off flashlight' : 'Turn on flashlight'}
            className="absolute bottom-3 right-3 rounded-full bg-black/50 p-2 text-white hover:bg-black/70"
          >
            {torchOn ? <FlashlightOff size={20} /> : <Flashlight size={20} />}
          </button>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/70">
            <div className="text-center p-4">
              <CameraOff className="mx-auto mb-2 text-red-400" size={32} />
              <p className="text-white text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Looking up a detected code — the stream is stopped while this
            shows. A miss/error resumes scanning automatically via
            `restartSignal`, no confirmation needed. */}
        {loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/70 p-4 text-center">
            <Loader2 className="animate-spin text-white" size={28} />
            <p className="text-sm text-gray-200">Looking up barcode…</p>
          </div>
        )}
      </div>

      <p className="text-sm text-center text-gray-500 dark:text-gray-400">
        {GUIDANCE_TEXT[guidance]}
      </p>

      <Button variant="outline" onClick={onClose}>
        Cancel scanning
      </Button>
    </div>
  )
}
