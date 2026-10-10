import * as React from "react"

// The URL hash without "#". Client navigation uses pushState, which neither fires hashchange
// nor updates CSS :target, so anchored rows read the hash from here instead.
function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange)
  window.addEventListener("popstate", onChange)
  return () => {
    window.removeEventListener("hashchange", onChange)
    window.removeEventListener("popstate", onChange)
  }
}

export function useHash() {
  return React.useSyncExternalStore(
    subscribe,
    () => decodeURIComponent(window.location.hash.slice(1)),
    () => ""
  )
}
