import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act, cleanup } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Library from './Library'
import { mediaApi } from '../api/media'
import { locationsApi } from '../api/locations'
import { platformsApi } from '../api/platforms'
import { mediaSubtypesApi } from '../api/mediaSubtypes'
import { listsApi } from '../api/lists'
import { useLibraryStore, useReferenceDataStore } from '../store'

vi.mock('../api/media', () => ({
  mediaApi: {
    list: vi.fn(),
    delete: vi.fn(),
  },
}))
vi.mock('../api/locations', () => ({ locationsApi: { list: vi.fn() } }))
vi.mock('../api/platforms', () => ({ platformsApi: { list: vi.fn() } }))
vi.mock('../api/mediaSubtypes', () => ({ mediaSubtypesApi: { list: vi.fn() } }))
vi.mock('../api/lists', () => ({ listsApi: { list: vi.fn() } }))

const mockSubtype = { id: 1, name: 'CD', category: 'music', supertype: 'physical', sort_order: 1 }

const mockItem = {
  id: 1,
  title: 'Abbey Road',
  category: 'music',
  artist: 'The Beatles',
  year: 1969,
  cover_thumb_url: null,
  cover_url: null,
  ownership: 'physical',
  supertype: 'physical',
  media_subtype: mockSubtype,
  linked_items: [],
  location_path: 'Living Room',
  location_name: 'Living Room',
}

function renderLibrary(initialPath = '/library/music') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/library/:category" element={<Library />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  locationsApi.list.mockResolvedValue([])
  platformsApi.list.mockResolvedValue([])
  mediaSubtypesApi.list.mockResolvedValue([mockSubtype])
  listsApi.list.mockResolvedValue([])
  useLibraryStore.setState({
    viewMode: 'grid',
    filters: {
      q: '', supertype: '', media_subtype_id: '', platform_id: '',
      genre: '', year: '', location_id: '', list_id: '', sort: 'created_at', order: 'desc',
    },
  })
  useReferenceDataStore.setState({ locations: [], platforms: [], mediaSubtypes: [], lists: [], loaded: false, loading: null })
})

afterEach(() => {
  cleanup()
})

describe('Library', () => {
  it('shows the empty-library state when there are no items and no filters', async () => {
    mediaApi.list.mockResolvedValue({ items: [], total: 0, page: 1, pages: 0, per_page: 24 })

    renderLibrary()

    expect(await screen.findByText('No music yet')).toBeTruthy()
    expect(screen.getByText('Add your first item')).toBeTruthy()
  })

  it('shows a no-results message when filters produce zero matches', async () => {
    useLibraryStore.setState((s) => ({ filters: { ...s.filters, q: 'nonexistent' } }))
    mediaApi.list.mockResolvedValue({ items: [], total: 0, page: 1, pages: 0, per_page: 24 })

    renderLibrary()

    expect(await screen.findByText('No results match your search')).toBeTruthy()
    expect(screen.queryByText('No music yet')).toBeNull()
  })

  it('renders items in grid view by default', async () => {
    mediaApi.list.mockResolvedValue({ items: [mockItem], total: 1, page: 1, pages: 1, per_page: 24 })

    renderLibrary()

    expect(await screen.findByText('Abbey Road')).toBeTruthy()
    expect(screen.getByText('The Beatles')).toBeTruthy()
    expect(screen.getByText('1969')).toBeTruthy()
    expect(screen.getByText('1 item')).toBeTruthy()
  })

  it('switches to list view when the list toggle is clicked', async () => {
    mediaApi.list.mockResolvedValue({ items: [mockItem], total: 1, page: 1, pages: 1, per_page: 24 })

    renderLibrary()
    await screen.findByText('Abbey Road')

    fireEvent.click(screen.getByTitle('list view (l)'))

    expect(useLibraryStore.getState().viewMode).toBe('list')
  })

  it('paginates through results', async () => {
    mediaApi.list.mockResolvedValue({ items: [mockItem], total: 50, page: 1, pages: 3, per_page: 24 })

    renderLibrary()
    await screen.findByText('Abbey Road')

    const prevButton = screen.getByText('Previous')
    const nextButton = screen.getByText('Next')
    expect(prevButton.disabled).toBe(true)
    expect(nextButton.disabled).toBe(false)

    mediaApi.list.mockResolvedValue({ items: [mockItem], total: 50, page: 2, pages: 3, per_page: 24 })
    fireEvent.click(nextButton)

    await waitFor(() => {
      expect(mediaApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2 }),
        expect.anything()
      )
    })
  })

  it('filters by list when a list is selected from the filter panel', async () => {
    listsApi.list.mockResolvedValue([{ id: 9, name: 'Want to relisten', category: 'music', item_count: 1 }])
    mediaApi.list.mockResolvedValue({ items: [mockItem], total: 1, page: 1, pages: 1, per_page: 24 })

    renderLibrary()
    await screen.findByText('Abbey Road')

    fireEvent.click(screen.getByText('All lists'))
    fireEvent.click(screen.getByText('Want to relisten'))

    await waitFor(() => {
      expect(mediaApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ list_id: '9' }),
        expect.anything()
      )
    })
  })

  it('debounces search input and reloads with the query', async () => {
    mediaApi.list.mockResolvedValue({ items: [], total: 0, page: 1, pages: 0, per_page: 24 })

    renderLibrary()
    await screen.findByText('No music yet')

    vi.useFakeTimers()
    try {
      const input = screen.getByPlaceholderText('Search titles, authors, directors… (press /)')
      fireEvent.change(input, { target: { value: 'Abbey' } })

      mediaApi.list.mockClear()
      await act(async () => {
        vi.advanceTimersByTime(300)
      })

      expect(useLibraryStore.getState().filters.q).toBe('Abbey')
      expect(mediaApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ q: 'Abbey' }),
        expect.anything()
      )
    } finally {
      vi.useRealTimers()
    }
  })

  it('redirects to the default category when the slug is unknown', async () => {
    mediaApi.list.mockResolvedValue({ items: [], total: 0, page: 1, pages: 0, per_page: 24 })

    renderLibrary('/library/not-a-real-category')

    expect(await screen.findByText('No music yet')).toBeTruthy()
  })
})
