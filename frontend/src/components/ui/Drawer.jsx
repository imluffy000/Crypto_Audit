import { useEffect, useRef } from 'react';

/**
 * Off-canvas panel (used for navigation on small screens). Closes on Escape and backdrop click,
 * moves focus inside when opened and restores it on close.
 */
function Drawer({ open, onClose, label, side = 'left', children }) {
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const panel = panelRef.current;
    panel?.querySelector('a, button, [tabindex]:not([tabindex="-1"])')?.focus();

    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
      if (event.key !== 'Tab' || !panel) return;
      const focusable = panel.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        last.focus();
        event.preventDefault();
      } else if (!event.shiftKey && document.activeElement === last) {
        first.focus();
        event.preventDefault();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
      previous?.focus?.();
    };
  }, [open, onClose]);

  return (
    <div className={`drawer drawer-${side} ${open ? 'is-open' : ''}`} aria-hidden={!open} inert={!open}>
      <div className="drawer-backdrop" onClick={onClose} />
      <div ref={panelRef} className="drawer-panel" role="dialog" aria-modal="true" aria-label={label}>
        {children}
      </div>
    </div>
  );
}

export default Drawer;
