import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import BatchModeStep from './BatchModeStep'

afterEach(() => {
  cleanup()
})

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
})
