import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import ListNameStep from './ListNameStep'
import { listsApi } from '../../api/lists'

vi.mock('../../api/lists', () => ({ listsApi: { create: vi.fn() } }))

afterEach(() => {
  cleanup()
})

describe('ListNameStep', () => {
  it('shows the category in the heading', () => {
    render(<ListNameStep category="books" onBack={vi.fn()} onCreated={vi.fn()} />)

    expect(screen.getByText('New Books list')).toBeTruthy()
  })

  it('disables Create until a name is entered', () => {
    render(<ListNameStep category="books" onBack={vi.fn()} onCreated={vi.fn()} />)

    expect(screen.getByText('Create').closest('button').disabled).toBe(true)

    fireEvent.change(screen.getByPlaceholderText('e.g. Want to read'), { target: { value: 'Want to read' } })

    expect(screen.getByText('Create').closest('button').disabled).toBe(false)
  })

  it('creates the list and calls onCreated', async () => {
    const created = { id: 7, name: 'Want to read', category: 'books', item_count: 0 }
    listsApi.create.mockResolvedValue(created)
    const onCreated = vi.fn()

    render(<ListNameStep category="books" onBack={vi.fn()} onCreated={onCreated} />)

    fireEvent.change(screen.getByPlaceholderText('e.g. Want to read'), { target: { value: 'Want to read' } })
    fireEvent.click(screen.getByText('Create'))

    await waitFor(() => {
      expect(listsApi.create).toHaveBeenCalledWith({ name: 'Want to read', category: 'books' })
    })
    expect(onCreated).toHaveBeenCalledWith(created)
  })

  it('calls onBack when Back is clicked', () => {
    const onBack = vi.fn()
    render(<ListNameStep category="books" onBack={onBack} onCreated={vi.fn()} />)

    fireEvent.click(screen.getByText('Back'))

    expect(onBack).toHaveBeenCalled()
  })
})
