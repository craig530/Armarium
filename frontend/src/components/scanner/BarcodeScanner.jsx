import { useEffect, useRef, useState } from 'react'
import {
  BrowserMultiFormatReader,
  NotFoundException,
  ChecksumException,
  FormatException,
  DecodeHintType,
  BarcodeFormat,
} from '@zxing/library'
import { CameraOff, Flashlight, FlashlightOff, Loader2 } from 'lucide-react'
import Button from '../ui/Button'

const SECURE_CONTEXT_ERROR =
  'Camera scanning requires a secure (HTTPS) connection. Use manual entry below, or access this site over HTTPS.'

// Books, CDs, DVDs and Blu-rays mostly use these retail barcode formats, plus
// Code128 (some library/AV-rental barcodes). Restricting to just these (with
// TRY_HARDER) avoids the default reader set — which also tries Code39/Code93/
// ITF/RSS — occasionally mis-decoding a UPC/EAN barcode as a different,
// shorter/garbled code under one of those formats.
const HINTS = new Map([
  [DecodeHintType.POSSIBLE_FORMATS, [
    BarcodeFormat.EAN_13,
    BarcodeFormat.EAN_8,
    BarcodeFormat.UPC_A,
    BarcodeFormat.UPC_E,
    BarcodeFormat.CODE_128,
  ]],
  [DecodeHintType.TRY_HARDER, true],
])

// Consecutive Checksum/Format misses (a barcode-like shape was seen but
// unreadable) before switching the guidance text to "hold steady".
const HOLD_STEADY_THRESHOLD = 3
// Consecutive plain "nothing in frame" misses before reverting back to the
// default guidance text.
const RESET_GUIDANCE_THRESHOLD = 5
// Minimum time between invalid-format flash/vibrate feedback for the same
// decoded text, so a held-up unsupported barcode doesn't flash every frame.
const INVALID_FLASH_COOLDOWN_MS = 1500

const GUIDANCE_TEXT = {
  default: 'Point your camera at a barcode',
  holdSteady: 'Hold steady — almost there',
}

// Mirrors the shape checks in `app/services/barcode.py::process_barcode` —
// used to decide whether a successful decode is a barcode we can actually
// look up, or just some other barcode-shaped code (e.g. a QR code or a
// foreign/garbled retail code) that should be flagged rather than accepted.
function looksLikeRecognizedBarcode(text) {
  const cleaned = (text || '').replace(/[\s-]/g, '')
  if (!/^\d+$/.test(cleaned)) return false
  const len = cleaned.length
  if ((cleaned.startsWith('978') || cleaned.startsWith('979')) && (len === 13 || len === 18)) return true
  return len === 8 || len === 12 || len === 13
}

// Maps the on-screen aim box onto the camera's source-pixel coordinates, so
// the decoder can crop to it. `object-cover` means whichever axis of the
// video is "wider" than the element gets cropped at render time — work out
// that visible region first, then map the aim box's rect into it.
function computeCropRegion(video, box) {
  const vw = video.videoWidth
  const vh = video.videoHeight
  const videoRect = video.getBoundingClientRect()
  const boxRect = box.getBoundingClientRect()
  if (!vw || !vh || !videoRect.width || !videoRect.height || !boxRect.width || !boxRect.height) {
    return null
  }

  const videoAspect = vw / vh
  const elAspect = videoRect.width / videoRect.height
  let visX = 0, visY = 0, visW = vw, visH = vh
  if (videoAspect > elAspect) {
    visW = vh * elAspect
    visX = (vw - visW) / 2
  } else if (videoAspect < elAspect) {
    visH = vw / elAspect
    visY = (vh - visH) / 2
  }

  const scaleX = visW / videoRect.width
  const scaleY = visH / videoRect.height

  const sx = Math.max(0, visX + (boxRect.left - videoRect.left) * scaleX)
  const sy = Math.max(0, visY + (boxRect.top - videoRect.top) * scaleY)
  const sWidth = Math.min(boxRect.width * scaleX, vw - sx)
  const sHeight = Math.min(boxRect.height * scaleY, vh - sy)
  if (sWidth <= 0 || sHeight <= 0) return null

  return { sx, sy, sWidth, sHeight }
}

// Decoding the full camera frame wastes most of its resolution on whatever
// is outside the aim box. Cropping to the aim box and upscaling it to fill
// the decode canvas acts as a digital zoom, giving the decoder far more
// effective resolution on small/distant barcodes (e.g. paperback ISBNs on a
// desktop webcam) without requiring a higher-resolution camera stream.
// Nearest-neighbour scaling (imageSmoothingEnabled = false) keeps bar/space
// edges sharp rather than blurring them together.
class ZoomingMultiFormatReader extends BrowserMultiFormatReader {
  cropRegion = null

  drawFrameOnCanvas(srcElement, dimensions, canvasElementContext) {
    const ctx = canvasElementContext || this.captureCanvasContext
    if (!dimensions && this.cropRegion && ctx) {
      ctx.imageSmoothingEnabled = false
      super.drawFrameOnCanvas(srcElement, {
        ...this.cropRegion,
        dx: 0,
        dy: 0,
        dWidth: srcElement.videoWidth,
        dHeight: srcElement.videoHeight,
      }, ctx)
      return
    }
    super.drawFrameOnCanvas(srcElement, dimensions, canvasElementContext)
  }
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

export default function BarcodeScanner({ onDetected, onClose, restartSignal, loading }) {
  const videoRef = useRef(null)
  const aimBoxRef = useRef(null)
  const readerRef = useRef(null)
  const cropCleanupRef = useRef(null)
  const missStreakRef = useRef({ notFound: 0, holdSteady: 0 })
  const lastInvalidRef = useRef({ text: null, time: 0 })
  const flashTimeoutRef = useRef(null)
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [error, setError] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [guidance, setGuidance] = useState('default')
  const [flash, setFlash] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [torchOn, setTorchOn] = useState(false)

  const startScanning = () => {
    const reader = readerRef.current
    if (!reader) return

    cropCleanupRef.current?.()
    cropCleanupRef.current = null

    setScanning(true)
    setError(null)
    setFlash(false)
    setGuidance('default')
    setTorchSupported(false)
    setTorchOn(false)
    missStreakRef.current = { notFound: 0, holdSteady: 0 }
    lastInvalidRef.current = { text: null, time: 0 }

    const flashInvalid = () => {
      setFlash(true)
      navigator.vibrate?.(200)
      clearTimeout(flashTimeoutRef.current)
      flashTimeoutRef.current = setTimeout(() => setFlash(false), 400)
    }

    // Asking for a higher resolution helps the decoder resolve small/dense
    // barcodes (e.g. paperback ISBNs) held further from the camera.
    // `decodeFromVideoDevice` builds these same constraints internally when
    // given a deviceId/facingMode — `decodeFromConstraints` lets us add the
    // resolution hints on top while keeping identical device-selection and
    // continuous-scanning behaviour.
    const videoConstraints = selectedDevice
      ? { deviceId: { exact: selectedDevice }, width: { ideal: 1920 }, height: { ideal: 1080 } }
      : isMobileDevice()
        ? { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
        : { width: { ideal: 1920 }, height: { ideal: 1080 } }

    reader
      .decodeFromConstraints({ video: videoConstraints }, videoRef.current, (result, err) => {
        if (result) {
          const text = result.getText()
          if (looksLikeRecognizedBarcode(text)) {
            // Pause the stream and hand off to the caller for a lookup.
            // A miss/error resumes scanning automatically via `restartSignal`
            // — there's no confirmation step, so a bad read just gets
            // silently rejected and scanning continues.
            reader.reset()
            setScanning(false)
            onDetected(text)
            return
          }
          // Barcode-shaped but not a format we can look up — flag it and
          // keep scanning rather than silently ignoring it.
          const now = Date.now()
          if (text !== lastInvalidRef.current.text || now - lastInvalidRef.current.time > INVALID_FLASH_COOLDOWN_MS) {
            lastInvalidRef.current = { text, time: now }
            flashInvalid()
          }
          return
        }

        // NotFoundException fires on every frame with no decodable code, and
        // ChecksumException/FormatException on a partial/garbled read — all
        // three are normal "keep scanning" outcomes, not camera errors.
        const isScanMiss =
          err instanceof NotFoundException ||
          err instanceof ChecksumException ||
          err instanceof FormatException
        if (!isScanMiss) {
          if (err) {
            setError(describeCameraError(err))
            setScanning(false)
          }
          return
        }

        const streak = missStreakRef.current
        if (err instanceof NotFoundException) {
          streak.holdSteady = 0
          streak.notFound += 1
          if (streak.notFound >= RESET_GUIDANCE_THRESHOLD) {
            setGuidance('default')
          }
        } else {
          streak.notFound = 0
          streak.holdSteady += 1
          if (streak.holdSteady >= HOLD_STEADY_THRESHOLD) {
            setGuidance('holdSteady')
          }
        }
      })
      .then(() => {
        // Device labels/ids are only populated after permission is granted —
        // re-enumerate now so the camera-switcher dropdown can show them.
        reader.listVideoInputDevices().then(setDevices).catch(() => {})

        // Torch is only available on some mobile rear cameras, and only once
        // the stream has actually started.
        const track = reader.stream?.getVideoTracks?.()[0]
        const capabilities = track?.getCapabilities?.()
        setTorchSupported(!!capabilities?.torch)

        // Compute the digital-zoom crop region once the stream's intrinsic
        // resolution is known, and keep it in sync with the aim box's
        // on-screen size (e.g. desktop window resize/orientation change).
        const updateCrop = () => {
          if (videoRef.current && aimBoxRef.current) {
            reader.cropRegion = computeCropRegion(videoRef.current, aimBoxRef.current)
          }
        }
        updateCrop()
        window.addEventListener('resize', updateCrop)
        cropCleanupRef.current = () => window.removeEventListener('resize', updateCrop)
      })
      .catch((e) => {
        setError(describeCameraError(e))
        setScanning(false)
      })
  }

  useEffect(() => {
    if (!isCameraSupported()) {
      setError(SECURE_CONTEXT_ERROR)
      return
    }

    const reader = readerRef.current ?? (readerRef.current = new ZoomingMultiFormatReader(HINTS))
    startScanning()

    return () => {
      reader.reset()
      cropCleanupRef.current?.()
      cropCleanupRef.current = null
      clearTimeout(flashTimeoutRef.current)
    }
  }, [selectedDevice]) // eslint-disable-line react-hooks/exhaustive-deps

  // Lets the caller force scanning to resume after a detected code turns out
  // to be a miss/error and the user stays on this screen — `reader.reset()`
  // already stopped the stream once a code was decoded, so resuming needs an
  // explicit restart.
  useEffect(() => {
    if (!restartSignal) return
    readerRef.current?.reset()
    startScanning()
  }, [restartSignal]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleTorch = async () => {
    const track = readerRef.current?.stream?.getVideoTracks?.()[0]
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
          value={selectedDevice || ''}
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
          <div ref={aimBoxRef} className="relative w-48 h-32">
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

        {/* Looking up a detected code — the stream is paused while this
            shows. A miss/error resumes scanning automatically, no
            confirmation needed. */}
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
