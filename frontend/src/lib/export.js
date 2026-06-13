import client from '../api/client'

// Downloads the user's library as a CSV or JSON file. Returns the file
// extension used, so callers can show a confirmation toast.
export async function exportLibrary(format) {
  const resp = await client.get(`/library/export?format=${format}`, { responseType: 'blob' })
  const ext = format === 'json' ? 'json' : 'csv'
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `armarium-export.${ext}`
  a.click()
  URL.revokeObjectURL(url)
  return ext
}

// Downloads a zip of all locally-stored cover images.
export async function exportCovers() {
  const resp = await client.get('/library/export/covers', { responseType: 'blob' })
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'armarium-covers.zip'
  a.click()
  URL.revokeObjectURL(url)
}
