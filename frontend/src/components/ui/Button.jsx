import { Link } from 'react-router-dom';
import { LoaderCircle } from 'lucide-react';

function classes(variant, size, block, iconOnly, className) {
  return ['btn', `btn-${variant}`, `btn-${size}`, block ? 'btn-block' : '', iconOnly ? 'btn-icon' : '', className || '']
    .filter(Boolean)
    .join(' ');
}

/**
 * Button, or a link styled as one when `to` (in-app route) or `href` (external/download) is given.
 * `icon` is a lucide component; `loading` swaps it for a spinner and disables the button.
 */
function Button({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  loading = false,
  block = false,
  to,
  href,
  children,
  className,
  disabled,
  type = 'button',
  ...rest
}) {
  const iconSize = size === 'sm' ? 14 : 16;
  const content = (
    <>
      {loading ? <LoaderCircle size={iconSize} className="spin" aria-hidden="true" /> : Icon ? <Icon size={iconSize} aria-hidden="true" /> : null}
      {children ? <span>{children}</span> : null}
    </>
  );
  const cls = classes(variant, size, block, !children, className);

  if (to && !disabled) {
    return (
      <Link to={to} className={cls} {...rest}>
        {content}
      </Link>
    );
  }
  if (href && !disabled) {
    return (
      <a href={href} className={cls} {...rest}>
        {content}
      </a>
    );
  }
  return (
    <button type={type} className={cls} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {content}
    </button>
  );
}

export default Button;
