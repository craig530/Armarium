import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLibraryStore } from '../store'

export function useKeyboardShortcuts() {
  const navigate = useNavigate()
  const { setViewMode } = useLibraryStore()

  useEffect(() => {
    const handler = (e) => {
      // Never fire when typing in form elements
      const tag = document.activeElement?.tagName
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
        // Only Escape should work inside inputs
        if (e.key === 'Escape') document.activeElement.blur()
        return
      }

      switch (e.key) {
        case '/':
          e.preventDefault()
          document.querySelector('[data-search]')?.focus()
          break
        case 'n':
          navigate('/add')
          break
        case 'g':
          setViewMode('grid')
          break
        case 'l':
          setViewMode('list')
          break
        case 'Escape':
          navigate(-1)
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate, setViewMode])
}
