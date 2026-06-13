import { useNavigate } from 'react-router-dom'
import AddFlow from '../components/add/AddFlow'

export default function AddItem() {
  const navigate = useNavigate()

  return (
    <div>
      <AddFlow onSaved={(item) => navigate(`/item/${item.id}`)} />
    </div>
  )
}
