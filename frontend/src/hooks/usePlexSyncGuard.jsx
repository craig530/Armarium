import { useEffect } from 'react'
import { useBlocker } from 'react-router-dom'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import { plexApi } from '../api/plex'

// Warns before the user navigates away from a page with a Plex sync still
// running in the background — `syncStatus` is `{[mappingId]: PlexSyncStatus}`.
// Covers both in-app navigation (via the data router's `useBlocker`) and
// tab close/refresh/typed-URL navigation (via `beforeunload`). Render the
// returned element near the top of the component tree.
export function usePlexSyncGuard(syncStatus) {
  const runningIds = Object.entries(syncStatus)
    .filter(([, status]) => status.status === 'running')
    .map(([id]) => Number(id))
  const hasRunningSync = runningIds.length > 0

  useEffect(() => {
    if (!hasRunningSync) return
    const handler = (e) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [hasRunningSync])

  const blocker = useBlocker(hasRunningSync)

  if (blocker.state !== 'blocked') return null

  const handleCancelAndLeave = async () => {
    await Promise.all(runningIds.map((id) => plexApi.cancelSync(id).catch(() => {})))
    blocker.proceed()
  }

  return (
    <Modal open title="Plex sync in progress" onClose={() => blocker.reset()}>
      <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
        A Plex library sync is still running. You can leave it running in the background, cancel
        it before you go, or stay on this page to watch its progress.
      </p>
      <div className="flex flex-col sm:flex-row sm:justify-end gap-2">
        <Button variant="ghost" onClick={() => blocker.reset()}>Stay</Button>
        <Button variant="secondary" onClick={() => blocker.proceed()}>Leave — keep syncing</Button>
        <Button variant="danger" onClick={handleCancelAndLeave}>Cancel sync & leave</Button>
      </div>
    </Modal>
  )
}
