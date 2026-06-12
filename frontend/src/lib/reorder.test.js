import { describe, it, expect } from 'vitest'
import { reorderSiblings } from './reorder'

describe('reorderSiblings', () => {
  it('breaks ties when all siblings share sort_order 0 (issue 8)', () => {
    const items = [
      { id: 1, sort_order: 0 },
      { id: 2, sort_order: 0 },
      { id: 3, sort_order: 0 },
    ]
    expect(reorderSiblings(items, 0, 1)).toEqual([
      { id: 1, sort_order: 1 },
      { id: 3, sort_order: 2 },
    ])
  })

  it('moves an item back up after a tie-break, restoring the original order', () => {
    // State after applying the updates from the previous test: item2 stayed
    // at 0, item1 moved to 1, item3 moved to 2.
    const items = [
      { id: 2, sort_order: 0 },
      { id: 1, sort_order: 1 },
      { id: 3, sort_order: 2 },
    ]
    expect(reorderSiblings(items, 1, -1)).toEqual([
      { id: 1, sort_order: 0 },
      { id: 2, sort_order: 1 },
    ])
  })

  it('swaps both items when moving within a sequentially-ordered group', () => {
    const items = [
      { id: 1, sort_order: 0 },
      { id: 2, sort_order: 1 },
      { id: 3, sort_order: 2 },
      { id: 4, sort_order: 3 },
    ]
    expect(reorderSiblings(items, 1, 1)).toEqual([
      { id: 3, sort_order: 1 },
      { id: 2, sort_order: 2 },
    ])
  })

  it('returns [] when moving the first item up', () => {
    const items = [
      { id: 1, sort_order: 0 },
      { id: 2, sort_order: 1 },
    ]
    expect(reorderSiblings(items, 0, -1)).toEqual([])
  })

  it('returns [] when moving the last item down', () => {
    const items = [
      { id: 1, sort_order: 0 },
      { id: 2, sort_order: 1 },
    ]
    expect(reorderSiblings(items, 1, 1)).toEqual([])
  })

  it('returns [] for an out-of-range index', () => {
    const items = [{ id: 1, sort_order: 0 }]
    expect(reorderSiblings(items, -1, 1)).toEqual([])
  })
})
