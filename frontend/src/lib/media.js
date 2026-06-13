// Merge linked copies (physical + any number of digital platforms) into a
// single card. Every item in a connected group carries `linked_items`
// listing all its partners, so once one member is rendered, the rest are
// skipped if they also appear on this page.
export function dedupeLinkedItems(items) {
  const consumed = new Set()
  const result = []
  for (const item of items || []) {
    if (consumed.has(item.id)) continue
    for (const linked of item.linked_items || []) {
      consumed.add(linked.id)
    }
    result.push(item)
  }
  return result
}
