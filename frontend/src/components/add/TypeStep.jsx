import { Disc3, Cloud, ListPlus } from 'lucide-react'
import clsx from 'clsx'
import { CATEGORIES, SUPERTYPES } from '../../lib/categories'
import { CATEGORY_ICONS } from '../../lib/mediaIcons'

const SUPERTYPE_ICONS = { physical: Disc3, digital: Cloud }

const TILE_BASE = 'flex flex-col items-center gap-2 py-4 rounded-xl text-sm font-medium transition-colors border'
const TILE_ACTIVE = 'bg-brand-600 text-white border-brand-600'
const TILE_INACTIVE = 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-transparent hover:bg-gray-200 dark:hover:bg-gray-700'

export default function TypeStep({ category, supertype, creatingList, onChangeCategory, onChangeSupertype, onSelectList }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">What are you adding?</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Choose a category, then physical or digital</p>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Category</p>
        <div className="grid grid-cols-4 gap-2">
          {CATEGORIES.map((c) => {
            const Icon = CATEGORY_ICONS[c.value]
            return (
              <button
                key={c.value}
                onClick={() => onChangeCategory(c.value)}
                className={clsx(TILE_BASE, 'py-3 sm:py-4 text-xs sm:text-sm', category === c.value ? TILE_ACTIVE : TILE_INACTIVE)}
              >
                <Icon size={20} />
                {c.label}
              </button>
            )
          })}
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Physical, digital, or a list?</p>
        <div className="grid grid-cols-3 gap-2">
          {SUPERTYPES.map((s) => {
            const Icon = SUPERTYPE_ICONS[s.value]
            return (
              <button
                key={s.value}
                onClick={() => onChangeSupertype(s.value)}
                className={clsx(TILE_BASE, !creatingList && supertype === s.value ? TILE_ACTIVE : TILE_INACTIVE)}
              >
                <Icon size={22} />
                {s.label}
              </button>
            )
          })}
          <button
            onClick={onSelectList}
            className={clsx(TILE_BASE, creatingList ? TILE_ACTIVE : TILE_INACTIVE)}
          >
            <ListPlus size={22} />
            List
          </button>
        </div>
      </div>
    </div>
  )
}
