// Built-in platform logo registry. Logos are extracted from `simple-icons`
// by scripts/extract-platform-logos.mjs into src/assets/icons/platforms/ as
// SVGs with the brand colour baked into `fill`, so they keep their identity
// in dark mode (unlike the line-style location icons, which use
// `currentColor`).
//
// Not every service in the spec has an official simple-icons entry — those
// have `logoUrl: null` and fall back to a generic platform icon until the
// user uploads a custom logo.
import plex from '../assets/icons/platforms/plex.svg'
import netflix from '../assets/icons/platforms/netflix.svg'
import appletv from '../assets/icons/platforms/appletv.svg'
import spotify from '../assets/icons/platforms/spotify.svg'
import applemusic from '../assets/icons/platforms/applemusic.svg'
import youtubemusic from '../assets/icons/platforms/youtubemusic.svg'
import tidal from '../assets/icons/platforms/tidal.svg'
import mubi from '../assets/icons/platforms/mubi.svg'
import nowtv from '../assets/icons/platforms/nowtv.svg'
import paramountplus from '../assets/icons/platforms/paramountplus.svg'
import hbomax from '../assets/icons/platforms/hbomax.svg'
import crunchyroll from '../assets/icons/platforms/crunchyroll.svg'

export const PLATFORM_LOGOS = {
  plex: { label: 'Plex', logoUrl: plex, aliases: [] },
  netflix: { label: 'Netflix', logoUrl: netflix, aliases: [] },
  amazon_prime_video: { label: 'Amazon Prime Video', logoUrl: null, aliases: ['amazon prime', 'prime video', 'amazon video'] },
  appletv: { label: 'Apple TV', logoUrl: appletv, aliases: ['apple tv+', 'apple tv plus'] },
  disney_plus: { label: 'Disney+', logoUrl: null, aliases: ['disney plus'] },
  spotify: { label: 'Spotify', logoUrl: spotify, aliases: [] },
  applemusic: { label: 'Apple Music', logoUrl: applemusic, aliases: [] },
  youtubemusic: { label: 'YouTube Music', logoUrl: youtubemusic, aliases: ['youtube music'] },
  tidal: { label: 'Tidal', logoUrl: tidal, aliases: [] },
  qobuz: { label: 'Qobuz', logoUrl: null, aliases: [] },
  mubi: { label: 'MUBI', logoUrl: mubi, aliases: [] },
  bfi_player: { label: 'BFI Player', logoUrl: null, aliases: ['bfi'] },
  nowtv: { label: 'NOW TV', logoUrl: nowtv, aliases: ['now', 'now tv'] },
  paramountplus: { label: 'Paramount+', logoUrl: paramountplus, aliases: ['paramount plus'] },
  peacock: { label: 'Peacock', logoUrl: null, aliases: [] },
  hbomax: { label: 'HBO Max', logoUrl: hbomax, aliases: ['max', 'hbo'] },
  crunchyroll: { label: 'Crunchyroll', logoUrl: crunchyroll, aliases: [] },
}

/** Find a built-in logo key matching a user-entered platform name (case-insensitive, exact or alias match). */
export function matchPlatformLogo(name) {
  if (!name) return null
  const normalized = name.trim().toLowerCase()
  for (const [key, entry] of Object.entries(PLATFORM_LOGOS)) {
    if (entry.label.toLowerCase() === normalized) return key
    if (entry.aliases.some((a) => a.toLowerCase() === normalized)) return key
  }
  return null
}

/** Resolve the display logo URL for a platform: custom upload > built-in logo_key > null. */
export function platformLogoUrl(platform) {
  if (!platform) return null
  if (platform.logo_url) return platform.logo_url
  if (platform.logo_key && PLATFORM_LOGOS[platform.logo_key]?.logoUrl) {
    return PLATFORM_LOGOS[platform.logo_key].logoUrl
  }
  return null
}
