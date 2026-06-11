import clsx from 'clsx'
import tmdbLogo from '../../assets/tmdb/blue_short.svg'

/**
 * Required attribution for data/images sourced from The Movie Database (TMDB).
 * See THIRD_PARTY_LICENSES.md for details on TMDB's API terms and logo usage.
 */
export default function TMDBAttribution({ className }) {
  return (
    <a
      href="https://www.themoviedb.org/"
      target="_blank"
      rel="noopener noreferrer"
      className={clsx(
        'inline-flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:underline',
        className
      )}
    >
      <img src={tmdbLogo} alt="TMDB" className="h-3.5 w-auto shrink-0" />
      <span>This product uses the TMDB API but is not endorsed or certified by TMDB.</span>
    </a>
  )
}
