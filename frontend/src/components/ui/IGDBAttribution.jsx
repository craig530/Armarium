import clsx from 'clsx'
import igdbLogo from '../../assets/igdb/logo.svg'

/**
 * Required attribution for data/images sourced from IGDB (Internet Game Database).
 * See THIRD_PARTY_LICENSES.md for details on IGDB's API terms and logo usage.
 * Logo sourced from https://commons.wikimedia.org/wiki/File:IGDB_logo.svg (CC BY-SA 4.0).
 */
export default function IGDBAttribution({ className }) {
  return (
    <a
      href="https://www.igdb.com/"
      target="_blank"
      rel="noopener noreferrer"
      className={clsx(
        'inline-flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:underline',
        className
      )}
    >
      <img src={igdbLogo} alt="IGDB" className="h-3.5 w-auto shrink-0 dark:invert" />
      <span>Game data from IGDB — not endorsed by IGDB.</span>
    </a>
  )
}
