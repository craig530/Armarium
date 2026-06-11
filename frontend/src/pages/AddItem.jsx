import { useNavigate, useLocation } from 'react-router-dom'
import AddFlow from '../components/add/AddFlow'

export default function AddItem() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div>
      {/* `location.key` changes on every navigation to /add (even repeat
          clicks on the same nav link), so keying on it forces a fresh
          remount and resets the workflow back to step one. */}
      <AddFlow key={location.key} onSaved={(item) => navigate(`/item/${item.id}`)} />
    </div>
  )
}
