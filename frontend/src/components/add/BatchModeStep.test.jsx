import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import BatchModeStep from './BatchModeStep'

afterEach(() => {
  cleanup()
})

const musicLists = [
  { id: 1, name: 'Favourites', category: 'music' },
  { id: 2, name: 'Road trip', category: 'music' },
]
const bookLists = [{ id: 3, name: 'Want to read', category: 'books' }]

describe('BatchModeStep', () => {
  it('shows the switch as off and calls onChange(true) when toggled', () => {
    const onChange = vi.fn()
    render(<BatchModeStep batchMode={false} onChange={onChange} onContinue={vi.fn()} />)

    const switchEl = screen.getByRole('switch')
    expect(switchEl.getAttribute('aria-checked')).toBe('false')

    fireEvent.click(screen.getByText('Enable batch mode'))

    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('shows the switch as on and calls onChange(false) when toggled', () => {
    const onChange = vi.fn()
    render(<BatchModeStep batchMode={true} onChange={onChange} onContinue={vi.fn()} />)

    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('true')

    fireEvent.click(screen.getByText('Enable batch mode'))

    expect(onChange).toHaveBeenCalledWith(false)
  })

  it('calls onContinue when the Continue button is clicked', () => {
    const onContinue = vi.fn()
    render(<BatchModeStep batchMode={false} onChange={vi.fn()} onContinue={onContinue} />)

    fireEvent.click(screen.getByText('Continue'))

    expect(onContinue).toHaveBeenCalled()
  })

  it('hides the list picker when no lists exist for the category', () => {
    render(
      <BatchModeStep
        batchMode={false}
        onChange={vi.fn()}
        onContinue={vi.fn()}
        category="music"
        lists={bookLists}
        batchListId=""
        onBatchListChange={vi.fn()}
      />
    )

    expect(screen.queryByLabelText('Default list (optional)')).toBeNull()
  })

  it('shows a list picker with matching lists when they exist', () => {
    render(
      <BatchModeStep
        batchMode={false}
        onChange={vi.fn()}
        onContinue={vi.fn()}
        category="music"
        lists={[...musicLists, ...bookLists]}
        batchListId=""
        onBatchListChange={vi.fn()}
      />
    )

    expect(screen.getByText('Default list (optional)')).toBeTruthy()
    expect(screen.getByRole('combobox')).toBeTruthy()
    expect(screen.getByText('Favourites')).toBeTruthy()
    expect(screen.getByText('Road trip')).toBeTruthy()
    expect(screen.queryByText('Want to read')).toBeNull()
  })

  it('calls onBatchListChange when a list is selected', () => {
    const onBatchListChange = vi.fn()
    render(
      <BatchModeStep
        batchMode={false}
        onChange={vi.fn()}
        onContinue={vi.fn()}
        category="music"
        lists={musicLists}
        batchListId=""
        onBatchListChange={onBatchListChange}
      />
    )

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })

    expect(onBatchListChange).toHaveBeenCalledWith('1')
  })
})
