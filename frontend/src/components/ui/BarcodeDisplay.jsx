import Barcode from 'react-barcode'
import clsx from 'clsx'
import { useThemeStore } from '../../store'

// EAN-13/UPC-A are what `services/barcode.py` normalises scanned codes to;
// anything else (e.g. a manually-entered code) falls back to CODE128, which
// can encode arbitrary text.
function formatFor(value) {
  if (/^\d{13}$/.test(value)) return 'EAN13'
  if (/^\d{12}$/.test(value)) return 'UPC'
  return 'CODE128'
}

// Renders a scanned item barcode as an actual barcode image, matching the
// card it sits in.
export default function BarcodeDisplay({ value, className }) {
  const dark = useThemeStore((s) => s.dark)

  return (
    <div className={clsx('inline-block', className)}>
      <Barcode
        value={value}
        format={formatFor(value)}
        background="transparent"
        lineColor={dark ? '#e5e7eb' : '#111827'}
        height={40}
        width={1.5}
        fontSize={12}
        margin={0}
      />
    </div>
  )
}
