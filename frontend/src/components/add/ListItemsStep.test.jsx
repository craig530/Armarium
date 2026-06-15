import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import ListItemsStep from './ListItemsStep'
import { mediaApi } from '../../api/media'

vi.mock('../../api/media', () => ({ mediaApi: { list: vi.fn(), update: vi.fn() } }))

const list = { id: 3, name: 'Want to read', category: 'books' }

const itemA = { id: 1, title: 'Dune', author: 'Frank Herbert', list_ids: [] }
const itemB = { id: 2, title: 'Foundation', author: 'Isaac Asimov', list_ids: [3] }

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('ListItemsStep', () => {
  it('loads and shows library items on mount', async () => {
    mediaApi.list.mockResolvedValue({ items: [itemA, itemB], total: 2, page: 1, pages: 1, per_page: 20 })

    render(<ListItemsStep list={list} onBack={vi.fn()} onDone={vi.fn()} />)

    expect(await screen.findByText('Dune')).toBeTruthy()
    expect(screen.getByText('Foundation')).toBeTruthy()
    expect(mediaApi.list).toHaveBeenCalledWith({ category: 'books', q: '', per_page: 20 })
  })

  it('shows a message when no items are found', async () => {
    mediaApi.list.mockResolvedValue({ items: [], total: 0, page: 1, pages: 0, per_page: 20 })

    render(<ListItemsStep list={list} onBack={vi.fn()} onDone={vi.fn()} />)

    expect(await screen.findByText('No items found.')).toBeTruthy()
  })

  it('adds an item to the list when "Add" is clicked', async () => {
    mediaApi.list.mockResolvedValue({ items: [itemA], total: 1, page: 1, pages: 1, per_page: 20 })
    mediaApi.update.mockResolvedValue({ ...itemA, list_ids: [3] })

    render(<ListItemsStep list={list} onBack={vi.fn()} onDone={vi.fn()} />)

    await screen.findByText('Dune')
    fireEvent.click(screen.getByText('Add'))

    await waitFor(() => {
      expect(mediaApi.update).toHaveBeenCalledWith(1, { list_ids: [3] })
    })
    expect(await screen.findByText('Added')).toBeTruthy()
  })

  it('removes an item from the list when "Added" is clicked', async () => {
    mediaApi.list.mockResolvedValue({ items: [itemB], total: 1, page: 1, pages: 1, per_page: 20 })
    mediaApi.update.mockResolvedValue({ ...itemB, list_ids: [] })

    render(<ListItemsStep list={list} onBack={vi.fn()} onDone={vi.fn()} />)

    await screen.findByText('Foundation')
    fireEvent.click(screen.getByText('Added'))

    await waitFor(() => {
      expect(mediaApi.update).toHaveBeenCalledWith(2, { list_ids: [] })
    })
    expect(await screen.findByText('Add')).toBeTruthy()
  })

  it('calls onBack and onDone', async () => {
    mediaApi.list.mockResolvedValue({ items: [], total: 0, page: 1, pages: 0, per_page: 20 })
    const onBack = vi.fn()
    const onDone = vi.fn()

    render(<ListItemsStep list={list} onBack={onBack} onDone={onDone} />)

    await screen.findByText('No items found.')
    fireEvent.click(screen.getByText('Back'))
    fireEvent.click(screen.getByText('Done'))

    expect(onBack).toHaveBeenCalled()
    expect(onDone).toHaveBeenCalled()
  })
})
