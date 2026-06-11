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

// Removes a location and all of its descendants from a flattened list —
// used when picking a *parent* for a location, so it can't be reparented
// under itself or one of its own children.
export function excludeLocationSubtree(flat, excludeId) {
  if (excludeId == null || excludeId === '') return flat
  const id = Number(excludeId)
  return flat.filter((loc) => loc.id !== id && !loc.ancestorIds.includes(id))
}
