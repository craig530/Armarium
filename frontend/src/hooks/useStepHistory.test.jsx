import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useStepHistory } from './useStepHistory'

// Exposes both the hook under test and the router's current location, so
// tests can assert on `location.pathname`/`location.key` alongside `stack`
// — e.g. to confirm a guarded back() never navigates off /add.
function useHarness(initialStack) {
  const stepHistory = useStepHistory(initialStack)
  const location = useLocation()
  return { ...stepHistory, location }
}

// Mirrors the real app's route shape — AddFlow is rendered inside a matched
// `<Route path="add">`, which `navigate('.')` needs in order to resolve
// relative to /add rather than the router root.
function renderAtAdd(initialStack) {
  return renderHook(() => useHarness(initialStack), {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={['/before', '/add']} initialIndex={1}>
        <Routes>
          <Route path="/before" element={<div />} />
          <Route path="/add" element={children} />
        </Routes>
      </MemoryRouter>
    ),
  })
}

describe('useStepHistory', () => {
  it('starts at the given initial stack', () => {
    const { result } = renderAtAdd(['search'])
    expect(result.current.stack).toEqual(['search'])
    expect(result.current.location.pathname).toBe('/add')
  })

  it('push() appends a step and records it in location.state', () => {
    const { result } = renderAtAdd(['search'])

    act(() => result.current.push('edition'))

    expect(result.current.stack).toEqual(['search', 'edition'])
    expect(result.current.location.state).toEqual({ stepStack: ['search', 'edition'] })
  })

  it('back() after a push restores the previous stack without leaving the route', () => {
    const { result } = renderAtAdd(['search'])

    act(() => result.current.push('edition'))
    act(() => result.current.push('form'))
    expect(result.current.stack).toEqual(['search', 'edition', 'form'])

    act(() => result.current.back())
    expect(result.current.stack).toEqual(['search', 'edition'])
    expect(result.current.location.pathname).toBe('/add')

    act(() => result.current.back())
    expect(result.current.stack).toEqual(['search'])
    expect(result.current.location.pathname).toBe('/add')
  })

  it('back() at the initial step is a no-op — it never navigates past the route', () => {
    const { result } = renderAtAdd(['search'])

    act(() => result.current.back())

    expect(result.current.stack).toEqual(['search'])
    expect(result.current.location.pathname).toBe('/add')
  })

  it('replaceStack() swaps the current step without adding a history entry', () => {
    const { result } = renderAtAdd(['search'])

    act(() => result.current.push('form'))
    expect(result.current.stack).toEqual(['search', 'form'])

    act(() => result.current.replaceStack(['search']))
    expect(result.current.stack).toEqual(['search'])

    // The 'form' push's history entry was replaced, not left behind — back()
    // from here is the initial step again, so it's a no-op.
    act(() => result.current.back())
    expect(result.current.stack).toEqual(['search'])
    expect(result.current.location.pathname).toBe('/add')
  })
})
