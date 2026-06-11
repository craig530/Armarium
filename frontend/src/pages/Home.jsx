import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { mediaApi } from '../api/media'
import { CATEGORIES } from '../lib/categories'
import { dedupeLinkedItems } from '../lib/media'
import MediaRow from '../components/media/MediaRow'
import Button from '../components/ui/Button'
import toast from 'react-hot-toast'

const ROW_PER_PAGE = 20

export default function Home() {
  const navigate = useNavigate()
  const [recent, setRecent] = useState(null)
  const [byCategory, setByCategory] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    Promise.all([
      mediaApi.list({ sort: 'created_at', order: 'desc', per_page: ROW_PER_PAGE }),
      ...CATEGORIES.map((c) =>
        mediaApi.list({ category: c.value, sort: 'created_at', order: 'desc', per_page: ROW_PER_PAGE })
      ),
    ])
      .then(([recentResult, ...categoryResults]) => {
        if (cancelled) return
        setRecent(recentResult)
        const map = {}
        CATEGORIES.forEach((c, i) => { map[c.value] = categoryResults[i] })
        setByCategory(map)
      })
      .catch((err) => toast.error(err.message))
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [])

  const isEmpty = !loading && recent && recent.total === 0

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">All</h1>

      {isEmpty && (
        <div className="text-center py-24 space-y-4">
          <div className="text-6xl">📦</div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Your collection is empty</h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
            Start cataloguing your music, films, TV and books — physical or digital.
          </p>
          <Button onClick={() => navigate('/add')} className="mx-auto">
            <Plus size={16} /> Add your first item
          </Button>
        </div>
      )}

      {!isEmpty && (
        <>
          <MediaRow
            title="Recently Added"
            items={recent ? dedupeLinkedItems(recent.items) : []}
            loading={loading}
          />
          {CATEGORIES.map((c) => (
            <MediaRow
              key={c.value}
              title={c.label}
              items={byCategory[c.value] ? dedupeLinkedItems(byCategory[c.value].items) : []}
              seeAllHref={`/library/${c.slug}`}
              loading={loading}
            />
          ))}
        </>
      )}
    </div>
  )
}
