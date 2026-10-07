import { useEffect, useState } from 'react';

const EXIT_MS = 160;

// Views that are one page with several URLs (repository tabs) do not animate between themselves.
export function pageKey(pathname) {
  if (/^\/repositor(y|ies)\//.test(pathname)) return '/repositories';
  return pathname;
}

/**
 * Delays a route change long enough for the current page to fade out, then shows the new one
 * (which fades in via CSS). Returns the location to render and whether the old page is leaving.
 */
export function usePageTransition(location) {
  const [shown, setShown] = useState(location);
  const [leaving, setLeaving] = useState(false);
  const changed = pageKey(location.pathname) !== pageKey(shown.pathname);

  // Same page, new URL (a tab, a query string): swap immediately. State updates during render
  // are React's documented way to adjust state to a changed prop.
  if (!changed && location !== shown) setShown(location);
  if (!changed && leaving) setLeaving(false);
  if (changed && !leaving) setLeaving(true);

  useEffect(() => {
    if (!leaving) return undefined;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const timer = window.setTimeout(() => {
      setShown(location);
      setLeaving(false);
      window.scrollTo({ top: 0, behavior: 'instant' });
    }, reduced ? 0 : EXIT_MS);
    return () => window.clearTimeout(timer);
  }, [leaving, location]);

  return { shown, leaving };
}
