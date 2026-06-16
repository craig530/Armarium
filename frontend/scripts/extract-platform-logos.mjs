// One-time extraction of brand logos from `simple-icons` into static SVG
// assets under src/assets/icons/platforms/. Re-run with `node
// scripts/extract-platform-logos.mjs` if PLATFORM_ICON_SOURCES below changes.
//
// Brand colours are baked into the SVG `fill` (not `currentColor`) so logos
// keep their brand identity in dark mode, per src/lib/platformLogos.js.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import * as si from 'simple-icons'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.join(__dirname, '../src/assets/icons/platforms')
fs.mkdirSync(outDir, { recursive: true })

// key -> simple-icons export name. Keys match src/lib/platformLogos.js.
export const PLATFORM_ICON_SOURCES = {
  plex: 'siPlex',
  netflix: 'siNetflix',
  appletv: 'siAppletv',
  spotify: 'siSpotify',
  applemusic: 'siApplemusic',
  youtubemusic: 'siYoutubemusic',
  tidal: 'siTidal',
  mubi: 'siMubi',
  nowtv: 'siNow',
  paramountplus: 'siParamountplus',
  hbomax: 'siHbomax',
  crunchyroll: 'siCrunchyroll',
  audible: 'siAudible',
  googleplay: 'siGoogleplay',
  youtube: 'siYoutube',
  bandcamp: 'siBandcamp',
  soundcloud: 'siSoundcloud',
  deezer: 'siDeezer',
  itunes: 'siItunes',
  sky: 'siSky',
  rakutentv: 'siRakuten',
  // Games
  steam: 'siSteam',
  playstation: 'siPlaystation',
  epicgames: 'siEpicgames',
  gogdotcom: 'siGogdotcom',
  itchdotio: 'siItchdotio',
}

for (const [key, importName] of Object.entries(PLATFORM_ICON_SOURCES)) {
  const icon = si[importName]
  if (!icon) {
    console.warn(`Skipping ${key}: ${importName} not found in simple-icons`)
    continue
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#${icon.hex}"><path d="${icon.path}"/></svg>\n`
  fs.writeFileSync(path.join(outDir, `${key}.svg`), svg)
  console.log(`Wrote ${key}.svg (${icon.title}, #${icon.hex})`)
}
