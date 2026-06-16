import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import OwnershipRow from './OwnershipRow'
import { useReferenceDataStore } from '../../store'

afterEach(() => {
  cleanup()
  useReferenceDataStore.setState({ lists: [], loaded: false, loading: null })
})

const physicalItem = {
  id: 1,
  supertype: 'physical',
  location_path: 'Living Room > Shelf',
  location_icon_key: null,
  location_icon_url: null,
  list_ids: [],
  linked_items: [],
}

const digitalItem = {
  id: 2,
  supertype: 'digital',
  platform: { id: 1, name: 'Kindle', logo_key: null },
  list_ids: [],
  linked_items: [],
}

describe('OwnershipRow', () => {
  it('renders a location chip for a physical item', () => {
    useReferenceDataStore.setState({ lists: [] })
    render(<MemoryRouter><OwnershipRow item={physicalItem} /></MemoryRouter>)
    expect(screen.getByText('Living Room > Shelf')).toBeTruthy()
  })

  it('renders a platform chip for a digital item', () => {
    useReferenceDataStore.setState({ lists: [] })
    render(<MemoryRouter><OwnershipRow item={digitalItem} /></MemoryRouter>)
    expect(screen.getByText('Kindle')).toBeTruthy()
  })

  it('renders a list chip for a list the item belongs to', () => {
    useReferenceDataStore.setState({
      lists: [{ id: 10, name: 'Favourites', category: 'music' }],
    })
    // physicalItem (1 ownership chip) + 1 list chip = 2 total, both visible
    render(<MemoryRouter><OwnershipRow item={{ ...physicalItem, list_ids: [10] }} /></MemoryRouter>)
    expect(screen.getByText('Favourites')).toBeTruthy()
  })

  it('collapses chips beyond MAX_VISIBLE_CHIPS into a +N badge', () => {
    useReferenceDataStore.setState({
      lists: [
        { id: 10, name: 'Favourites', category: 'music' },
        { id: 11, name: 'Road trip', category: 'music' },
      ],
    })
    // 1 ownership chip + 2 list chips = 3 total → 1 overflow
    render(<MemoryRouter><OwnershipRow item={{ ...physicalItem, list_ids: [10, 11] }} /></MemoryRouter>)
    expect(screen.getByText('Favourites')).toBeTruthy()
    expect(screen.getByText('+1')).toBeTruthy()
  })

  it('renders nothing when there are no chips at all', () => {
    useReferenceDataStore.setState({ lists: [] })
    // An item with no physical/digital supertype has no ownership chips
    const { container } = render(<MemoryRouter><OwnershipRow item={{ id: 99, supertype: 'list', list_ids: [], linked_items: [] }} /></MemoryRouter>)
    expect(container.firstChild).toBeNull()
  })
})
