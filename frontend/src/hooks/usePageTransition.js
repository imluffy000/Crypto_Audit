import { useLayoutEffect } from 'react';

// Views that are one page with several URLs (repository tabs) do not animate between themselves.
export function pageKey(pathname) {
  if (/^\/repositor(y|ies)\//.test(pathname)) return '/repositories';
  return pathname;
}

/**
 * Route changes switch pages immediately (the new page fades in briefly via CSS, nothing waits for the
 * old one). This hook returns the key that restarts that fade and scrolls to the top on a new page.
 */
export function usePageTransition(location) {
  const key = pageKey(location.pathname);

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [key]);

  return key;
}
