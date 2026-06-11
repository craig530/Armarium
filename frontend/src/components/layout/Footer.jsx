const LICENSES_URL = 'https://github.com/craig530/Armarium/blob/main/THIRD_PARTY_LICENSES.md'

export default function Footer() {
  return (
    <footer className="mx-auto max-w-7xl px-4 py-6 mt-8 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-400 dark:text-gray-500 space-y-1">
      <p>
        Armarium is open source software. Third party licences and attributions are listed in{' '}
        <a href={LICENSES_URL} target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-gray-600 dark:hover:text-gray-300">
          THIRD_PARTY_LICENSES.md
        </a>
        .
      </p>
      <p>
        Armarium is not affiliated with, endorsed by, or sponsored by TMDB, MusicBrainz/MetaBrainz, Open Library,
        the Internet Archive, or any streaming, music or video platform referenced in this app. All product names,
        logos and brands are property of their respective owners.
      </p>
    </footer>
  )
}
