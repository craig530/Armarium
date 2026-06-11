// Merge linked physical/digital pairs into a single card. Both items in a
// pair carry a `linked_item` cross-reference (bidirectional), so once one
// side is rendered, its partner is skipped if it also appears on this page.
export function dedupeLinkedItems(items) {
  const consumed = new Set()
  const result = []
  for (const item of items || []) {
    if (consumed.has(item.id)) continue
    if (item.linked_item) consumed.add(item.linked_item.id)
    result.push(item)
  }
  return result
}
