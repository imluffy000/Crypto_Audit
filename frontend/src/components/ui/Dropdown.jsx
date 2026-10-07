import { useEffect, useId, useRef, useState } from 'react';

/**
 * Menu button. `items`: [{ label, icon, onSelect } | { label, icon, href, external }].
 * Escape closes and returns focus to the trigger; arrow keys move between items.
 */
function Dropdown({ trigger, triggerLabel, items, align = 'start', placement = 'bottom' }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const onPointer = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onPointer);
    rootRef.current?.querySelector('[role="menuitem"]')?.focus();
    return () => document.removeEventListener('mousedown', onPointer);
  }, [open]);

  const onMenuKeyDown = (event) => {
    const entries = Array.from(rootRef.current?.querySelectorAll('[role="menuitem"]') || []);
    const index = entries.indexOf(document.activeElement);
    if (event.key === 'Escape') {
      setOpen(false);
      buttonRef.current?.focus();
    } else if (event.key === 'ArrowDown') {
      entries[(index + 1) % entries.length]?.focus();
    } else if (event.key === 'ArrowUp') {
      entries[(index - 1 + entries.length) % entries.length]?.focus();
    } else if (event.key === 'Tab') {
      setOpen(false);
      return;
    } else {
      return;
    }
    event.preventDefault();
  };

  return (
    <div className="dropdown" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="dropdown-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={triggerLabel}
        onClick={() => setOpen((value) => !value)}
      >
        {trigger}
      </button>
      {open ? (
        <div id={menuId} role="menu" className={`dropdown-menu align-${align} place-${placement}`} onKeyDown={onMenuKeyDown}>
          {items.map(({ label, icon: Icon, onSelect, href, external }) =>
            href ? (
              <a key={label} role="menuitem" href={href} className="dropdown-item" target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined} onClick={() => setOpen(false)}>
                {Icon ? <Icon size={15} aria-hidden="true" /> : null}
                {label}
              </a>
            ) : (
              <button
                key={label}
                role="menuitem"
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setOpen(false);
                  onSelect();
                }}
              >
                {Icon ? <Icon size={15} aria-hidden="true" /> : null}
                {label}
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  );
}

export default Dropdown;
