import ListManager from '../../components/lists/ListManager'

export default function SettingsLists() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Lists</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Curated collections within each category, e.g. &quot;Want to read&quot;, &quot;Favourites&quot;.
        </p>
      </div>

      <div className="rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5">
        <ListManager />
      </div>
    </div>
  )
}
