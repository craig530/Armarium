import LocationManager from '../components/locations/LocationManager'

export default function Locations() {
  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Locations</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Organise where your physical media lives using a hierarchical structure.
        </p>
      </div>

      <div className="rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-5">
        <LocationManager />
      </div>
    </div>
  )
}
