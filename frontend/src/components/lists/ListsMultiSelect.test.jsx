import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import ListsMultiSelect from './ListsMultiSelect'
import { useReferenceDataStore } from '../../store'

afterEach(() => {
  cleanup()
})

describe('ListsMultiSelect', () => {
  it('renders nothing when there are no lists for the category', () => {
    useReferenceDataStore.setState({ lists: [], loaded: true, loading: null })

    const { container } = render(<ListsMultiSelect category="music" value={[]} onChange={vi.fn()} />)

    expect(container.firstChild).toBeNull()
  })

  it('only shows lists matching the given category', () => {
    useReferenceDataStore.setState({
      lists: [
        { id: 1, name: 'Favourites', category: 'music', item_count: 0 },
        { id: 2, name: 'Want to read', category: 'books', item_count: 0 },
      ],
      loaded: true, loading: null,
    })

    render(<ListsMultiSelect category="music" value={[]} onChange={vi.fn()} />)

    expect(screen.getByText('Favourites')).toBeTruthy()
    expect(screen.queryByText('Want to read')).toBeNull()
  })

  it('calls onChange with the list added when an inactive chip is clicked', () => {
    useReferenceDataStore.setState({
      lists: [{ id: 1, name: 'Favourites', category: 'music', item_count: 0 }],
      loaded: true, loading: null,
    })
    const onChange = vi.fn()

    render(<ListsMultiSelect category="music" value={[]} onChange={onChange} />)

    fireEvent.click(screen.getByText('Favourites'))

    expect(onChange).toHaveBeenCalledWith([1])
  })

  it('calls onChange with the list removed when an active chip is clicked', () => {
    useReferenceDataStore.setState({
      lists: [{ id: 1, name: 'Favourites', category: 'music', item_count: 0 }],
      loaded: true, loading: null,
    })
    const onChange = vi.fn()

    render(<ListsMultiSelect category="music" value={[1]} onChange={onChange} />)

    fireEvent.click(screen.getByText('Favourites'))

    expect(onChange).toHaveBeenCalledWith([])
  })
})
