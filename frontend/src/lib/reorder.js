// Computes the `sort_order` writes needed to move `items[idx]` one step in
// `direction` (-1 or +1), re-sequencing the whole group to 0..N-1 in the new
// order rather than swapping the two `sort_order` values directly. A direct
// swap is a no-op when siblings are tied (new rows default to
// `sort_order: 0`), so ties need breaking by writing every entry whose
// target index differs from its current `sort_order`.
//
// `items` must already be in display order (sort_order, then name, as
// returned by the API). Each item needs an `id` and `sort_order`. Returns
// `[]` if the move is out of bounds (already first/last).
export function reorderSiblings(items, idx, direction) {
  const swapIdx = idx + direction
  if (idx < 0 || swapIdx < 0 || swapIdx >= items.length) return []

  const reordered = [...items]
  ;[reordered[idx], reordered[swapIdx]] = [reordered[swapIdx], reordered[idx]]

  return reordered
    .map((item, i) => ({ id: item.id, sort_order: i, changed: item.sort_order !== i }))
    .filter((u) => u.changed)
    .map(({ id, sort_order }) => ({ id, sort_order }))
}
