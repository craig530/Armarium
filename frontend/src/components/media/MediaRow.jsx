import { useRef, useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, ChevronLeft } from 'lucide-react'
import clsx from 'clsx'
import MediaCard from './MediaCard'
import { SkeletonCard } from '../ui/Skeleton'

const CARD_WIDTH = 'w-32 sm:w-36 md:w-40 shrink-0'
const SCROLL_BY = 480

// Plex-style horizontal-scroll shelf used on the Home ("All") view.
export default function MediaRow({ title, count, items, seeAllHref, loading }) {
  const scrollRef = useRef(null)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(false)
  const isDragging = useRef(false)
  const startX = useRef(0)
  const scrollStart = useRef(0)
  const didDrag = useRef(false)

  const updateArrows = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setCanLeft(el.scrollLeft > 1)
    setCanRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 1)
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    updateArrows()
    const ro = new ResizeObserver(updateArrows)
    ro.observe(el)
    return () => ro.disconnect()
  }, [items, loading, updateArrows])

  const scrollLeft = () => scrollRef.current?.scrollBy({ left: -SCROLL_BY, behavior: 'smooth' })
  const scrollRight = () => scrollRef.current?.scrollBy({ left: SCROLL_BY, behavior: 'smooth' })

  const handleMouseDown = (e) => {
    if (!scrollRef.current) return
    isDragging.current = true
    didDrag.current = false
    startX.current = e.pageX - scrollRef.current.offsetLeft
    scrollStart.current = scrollRef.current.scrollLeft
    scrollRef.current.style.cursor = 'grabbing'
    scrollRef.current.style.userSelect = 'none'
  }

  const handleMouseMove = (e) => {
    if (!isDragging.current || !scrollRef.current) return
    const x = e.pageX - scrollRef.current.offsetLeft
    const walk = x - startX.current
    if (Math.abs(walk) > 4) didDrag.current = true
    scrollRef.current.scrollLeft = scrollStart.current - walk
  }

  const handleMouseUp = () => {
    isDragging.current = false
    if (scrollRef.current) {
      scrollRef.current.style.cursor = ''
      scrollRef.current.style.userSelect = ''
    }
  }

  // Prevent click-through after a drag gesture
  const handleClickCapture = (e) => {
    if (didDrag.current) {
      e.stopPropagation()
      didDrag.current = false
    }
  }

  const showNavButtons = !loading && (canLeft || canRight)

  if (!loading && (!items || items.length === 0)) return null

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-baseline gap-2 min-w-0">
          <span className="truncate">{title}</span>
          {count != null && (
            <span className="text-sm font-normal text-gray-400 dark:text-gray-500 shrink-0">
              {count.toLocaleString()}
            </span>
          )}
        </h2>
        <div className="flex items-center gap-1 shrink-0">
          {showNavButtons && (
            <>
              <button
                onClick={scrollLeft}
                disabled={!canLeft}
                className={clsx(
                  'h-7 w-7 flex items-center justify-center rounded-md transition-colors',
                  canLeft
                    ? 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
                    : 'text-gray-300 dark:text-gray-700 cursor-default'
                )}
                aria-label="Scroll left"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={scrollRight}
                disabled={!canRight}
                className={clsx(
                  'h-7 w-7 flex items-center justify-center rounded-md transition-colors',
                  canRight
                    ? 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
                    : 'text-gray-300 dark:text-gray-700 cursor-default'
                )}
                aria-label="Scroll right"
              >
                <ChevronRight size={16} />
              </button>
            </>
          )}
          {seeAllHref && (
            <Link
              to={seeAllHref}
              className="flex items-center gap-0.5 text-sm text-brand-600 dark:text-brand-400 hover:underline pl-1"
            >
              See all <ChevronRight size={14} />
            </Link>
          )}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-hide snap-x snap-mandatory select-none"
        onScroll={updateArrows}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClickCapture={handleClickCapture}
      >
        {loading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={`${CARD_WIDTH} snap-start`}>
                <SkeletonCard />
              </div>
            ))
          : items.map((item) => (
              <div key={item.id} className={`${CARD_WIDTH} snap-start`}>
                <MediaCard item={item} />
              </div>
            ))}
      </div>
    </section>
  )
}
