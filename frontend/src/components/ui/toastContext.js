import { createContext, useContext } from 'react';

export const ToastContext = createContext(() => {});

/** Returns `notify({ tone, title, message })`. Tones: info | success | warning | danger. */
export function useToast() {
  return useContext(ToastContext);
}
