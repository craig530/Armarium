import { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// Manages a step-stack wizard's navigation so that browser/gesture "back"
// steps back through the wizard (popping the stack) instead of leaving the
// current route entirely.
//
// Each push() also pushes a same-route history entry carrying the new stack
// in location.state, and back() goes through navigate(-1) — so the in-app
// back control and hardware/gesture back both land on the popstate-driven
// sync effect below, and a component using this hook can stay mounted
// (preserving any other state it holds) across these in-place navigations.
// Popping past the step this hook started on exits the route as normal.
export function useStepHistory(initialStack) {
  const navigate = useNavigate()
  const location = useLocation()

  const [stack, setStack] = useState(initialStack)
  const initialStackRef = useRef(initialStack)
  const lastSyncedKeyRef = useRef(location.key)

  const push = (name) => {
    const newStack = [...stack, name]
    setStack(newStack)
    navigate('.', { state: { stepStack: newStack } })
  }

  const back = () => {
    if (stack.length > 1) navigate(-1)
  }

  // Replaces (rather than pushes) the current history entry's stack — for
  // resets that return to an earlier step "in place" rather than as a new
  // step the user should be able to back out of independently.
  const replaceStack = (newStack) => {
    setStack(newStack)
    navigate('.', { state: { stepStack: newStack }, replace: true })
  }

  // Restores the stack when the user navigates back/forward through the
  // history entries push() created above. Skips the initial mount and the
  // re-render caused by push()/replaceStack()'s own navigate (which already
  // applied the same stack via setStack).
  useEffect(() => {
    if (location.key === lastSyncedKeyRef.current) return
    lastSyncedKeyRef.current = location.key
    setStack(location.state?.stepStack ?? initialStackRef.current)
  }, [location])

  return { stack, push, back, replaceStack }
}
