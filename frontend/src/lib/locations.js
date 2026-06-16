// Flattens the nested location tree (as returned by GET /locations) into a
// single list, computing each location's full breadcrumb path (e.g.
// "Living Room → Bookshelf → Shelf 2") and depth so pickers can render an
// indented, unambiguous list even when names repeat across branches.
export function flattenLocations(locations, parentPath = [], parentIds = [], depth = 0) {
  const result = []
  for (const loc of locations || []) {
    const path = [...parentPath, loc.name]
    const ancestorIds = [...parentIds, loc.id]
    result.push({ ...loc, depth, path: path.join(' → '), ancestorIds: parentIds })
    if (loc.children?.length) {
      result.push(...flattenLocations(loc.children, path, ancestorIds, depth + 1))
    }
  }
  return result
}

// Given a flat location list and a set of location IDs that are directly
// used by items, return the set of IDs that should appear in a filter picker:
// every used location plus all its ancestors (so the user can filter by a
// parent location and still find items in sub-locations).
export function reachableLocationIds(flat, usedIds) {
  const used = new Set(usedIds)
  const reachable = new Set()
  for (const loc of flat) {
    if (used.has(loc.id)) {
      reachable.add(loc.id)
      for (const aid of loc.ancestorIds) reachable.add(aid)
    }
  }
  return reachable
}

// Removes a location and all of its descendants from a flattened list —
// used when picking a *parent* for a location, so it can't be reparented
// under itself or one of its own children.
export function excludeLocationSubtree(flat, excludeId) {
  if (excludeId == null || excludeId === '') return flat
  const id = Number(excludeId)
  return flat.filter((loc) => loc.id !== id && !loc.ancestorIds.includes(id))
}
