import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import TypeStep from './TypeStep'

afterEach(() => {
  cleanup()
})

describe('TypeStep', () => {
  it('renders a tile for every category and supertype', () => {
    render(<TypeStep category={null} supertype={null} onChangeCategory={vi.fn()} onChangeSupertype={vi.fn()} />)

    expect(screen.getByText('Music')).toBeTruthy()
    expect(screen.getByText('Films & TV')).toBeTruthy()
    expect(screen.getByText('Books')).toBeTruthy()
    expect(screen.getByText('Physical')).toBeTruthy()
    expect(screen.getByText('Digital')).toBeTruthy()
  })

  it('calls onChangeCategory with the selected category value', () => {
    const onChangeCategory = vi.fn()
    render(<TypeStep category={null} supertype={null} onChangeCategory={onChangeCategory} onChangeSupertype={vi.fn()} />)

    fireEvent.click(screen.getByText('Films & TV'))

    expect(onChangeCategory).toHaveBeenCalledWith('films_tv')
  })

  it('calls onChangeSupertype with the selected supertype value', () => {
    const onChangeSupertype = vi.fn()
    render(<TypeStep category={null} supertype={null} onChangeCategory={vi.fn()} onChangeSupertype={onChangeSupertype} />)

    fireEvent.click(screen.getByText('Digital'))

    expect(onChangeSupertype).toHaveBeenCalledWith('digital')
  })

  it('highlights the currently selected category and supertype', () => {
    render(<TypeStep category="music" supertype="physical" onChangeCategory={vi.fn()} onChangeSupertype={vi.fn()} />)

    expect(screen.getByText('Music').closest('button').className).toContain('bg-brand-600')
    expect(screen.getByText('Physical').closest('button').className).toContain('bg-brand-600')
    expect(screen.getByText('Books').closest('button').className).not.toContain('bg-brand-600')
  })

  it('renders a "List" tile and calls onSelectList when clicked', () => {
    const onSelectList = vi.fn()
    render(
      <TypeStep
        category={null}
        supertype={null}
        onChangeCategory={vi.fn()}
        onChangeSupertype={vi.fn()}
        onSelectList={onSelectList}
      />
    )

    fireEvent.click(screen.getByText('List'))

    expect(onSelectList).toHaveBeenCalled()
  })

  it('highlights the "List" tile when creatingList is true, and not the supertypes', () => {
    render(
      <TypeStep
        category="music"
        supertype={null}
        creatingList
        onChangeCategory={vi.fn()}
        onChangeSupertype={vi.fn()}
        onSelectList={vi.fn()}
      />
    )

    expect(screen.getByText('List').closest('button').className).toContain('bg-brand-600')
    expect(screen.getByText('Physical').closest('button').className).not.toContain('bg-brand-600')
    expect(screen.getByText('Digital').closest('button').className).not.toContain('bg-brand-600')
  })
})
