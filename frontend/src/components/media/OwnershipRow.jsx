import { useState, useRef } from 'react'
import { Tv, Tag } from 'lucide-react'
import clsx from 'clsx'
import { useNavigate } from 'react-router-dom'
import { useReferenceDataStore, useLibraryStore } from '../../store'
import { CATEGORIES } from '../../lib/categories'
import LocationIcon from '../ui/LocationIcon'
import { platformLogoUrl } from '../../lib/platformLogos'

function IconBox({ children }) {
  return (
    <span className="shrink-0 h-5 w-5 rounded-sm bg-white dark:bg-gray-900 flex items-center justify-center p-0.5">
      {children}
    </span>
  )
}

// Styled hover tooltip for desktop — hidden on touch-only devices.
function HoverTooltip({ content, children }) {
  if (!content) return children
  return (
    <span className="relative group/tooltip">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-50 hidden group-hover/tooltip:block px-2 py-1 rounded text-xs text-white bg-gray-900 dark:bg-gray-700 shadow-lg whitespace-nowrap">
        {content}
      </span>
    </span>
  )
}

function LocationChip({ record }) {
  const [showPath, setShowPath] = useState(false)
  const timerRef = useRef(null)
  // Track whether long-press actually fired so endPress can suppress card navigation.
  const activatedRef = useRef(false)
  const path = record.location_path || null
  const name = record.location_name || record.location_path || 'No location'
  const hasHierarchy = path && name !== path

  const startPress = () => {
    if (!hasHierarchy) return
    timerRef.current = setTimeout(() => {
      activatedRef.current = true
      setShowPath(true)
    }, 500)
  }
  const cancelPress = () => {
    clearTimeout(timerRef.current)
    activatedRef.current = false
  }
  const endPress = (e) => {
    const wasActivated = activatedRef.current
    clearTimeout(timerRef.current)
    activatedRef.current = false
    if (wasActivated) {
      // Prevent the synthetic click that follows touchend from navigating the parent card.
      e.stopPropagation()
      e.preventDefault()
      setTimeout(() => setShowPath(false), 1800)
    }
  }

  return (
    <HoverTooltip content={hasHierarchy ? path : null}>
      <span
        className="relative inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 min-w-0 max-w-[12rem]"
        onClick={(e) => e.stopPropagation()}
        onTouchStart={startPress}
        onTouchEnd={endPress}
        onTouchMove={cancelPress}
      >
        <IconBox>
          <LocationIcon
            location={{ icon_key: record.location_icon_key, icon_url: record.location_icon_url }}
            size={12}
          />
        </IconBox>
        <span className="truncate">{name}</span>
        {showPath && path && (
          <span className="absolute bottom-full left-0 mb-1 z-50 bg-gray-900 dark:bg-gray-700 text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap max-w-[220px] overflow-hidden text-ellipsis">
            {path}
          </span>
        )}
      </span>
    </HoverTooltip>
  )
}

function PlatformChip({ record }) {
  const url = platformLogoUrl(record.platform)
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 min-w-0 max-w-[12rem]">
      <IconBox>
        {url ? <img src={url} alt="" className="h-full w-full object-contain" /> : <Tv size={12} className="text-gray-400" />}
      </IconBox>
      <span className="truncate">{record.platform?.name || 'No platform'}</span>
    </span>
  )
}

function ListChip({ name, onClick }) {
  return (
    <span
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick ? (e) => { e.stopPropagation(); onClick() } : undefined}
      className={clsx(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-brand-50 dark:bg-brand-900/30 text-xs text-brand-700 dark:text-brand-300 min-w-0 max-w-[12rem]',
        onClick && 'cursor-pointer hover:bg-brand-100 dark:hover:bg-brand-800/50'
      )}
    >
      <Tag size={10} className="shrink-0 opacity-70" />
      <span className="truncate">{name}</span>
    </span>
  )
}

const MAX_VISIBLE_CHIPS = 2

export default function OwnershipRow({ item, className }) {
  const navigate = useNavigate()
  const { lists } = useReferenceDataStore()

  const members = [item, ...(item.linked_items || [])].filter(
    (m) => m.supertype === 'physical' || m.supertype === 'digital'
  )

  const ownershipChips = members.map((m) =>
    m.supertype === 'physical'
      ? {
          key: `loc-${m.id}`,
          node: <LocationChip record={m} />,
          label: m.location_path || m.location_name || 'No location',
        }
      : {
          key: `plat-${m.id}`,
          node: <PlatformChip record={m} />,
          label: m.platform?.name || 'No platform',
        }
  )

  const listChips = (item.list_ids || [])
    .map((id) => lists.find((l) => l.id === id))
    .filter(Boolean)
    .map((l) => ({
      key: `list-${l.id}`,
      node: (
        <ListChip
          name={l.name}
          onClick={() => {
            const slug = CATEGORIES.find((c) => c.value === item.category)?.slug
            useLibraryStore.getState().setFilter('list_id', String(l.id))
            navigate(slug ? `/library/${slug}` : '/library')
          }}
        />
      ),
      label: l.name,
    }))

  const allChips = [...ownershipChips, ...listChips]
  if (allChips.length === 0) return null

  const visible = allChips.slice(0, MAX_VISIBLE_CHIPS)
  const overflow = allChips.slice(MAX_VISIBLE_CHIPS)

  return (
    <div className={clsx('flex items-center gap-1.5 flex-wrap overflow-hidden', className)}>
      {visible.map((c) => (
        <span key={c.key} className="min-w-0">{c.node}</span>
      ))}
      {overflow.length > 0 && (
        <HoverTooltip content={overflow.map((c) => c.label).join(', ')}>
          <span
            className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            +{overflow.length}
          </span>
        </HoverTooltip>
      )}
    </div>
  )
}
