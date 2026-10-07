import { useId, useState } from 'react';

/**
 * Text tooltip shown on hover and keyboard focus, described via aria-describedby.
 * Pass `focusable` when the child is not itself focusable (e.g. a badge) so keyboard users can reach it.
 */
function Tooltip({ content, children, placement = 'top', focusable = false }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  if (!content) return children;

  return (
    <span
      className="tooltip-wrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
      aria-describedby={id}
      tabIndex={focusable ? 0 : undefined}
    >
      {children}
      <span role="tooltip" id={id} className={`tooltip tooltip-${placement} ${open ? 'is-open' : ''}`}>
        {content}
      </span>
    </span>
  );
}

export default Tooltip;
