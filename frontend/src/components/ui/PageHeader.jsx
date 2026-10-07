import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

/** Page title block: optional breadcrumbs, title, supporting line, metadata and right-aligned actions. */
function PageHeader({ breadcrumbs = [], title, description, meta, actions, mono = false }) {
  return (
    <header className="page-header">
      {breadcrumbs.length ? (
        <nav aria-label="Breadcrumb" className="breadcrumbs">
          <ol>
            {breadcrumbs.map((crumb, index) => (
              <li key={`${crumb.label}-${index}`}>
                {crumb.to ? <Link to={crumb.to}>{crumb.label}</Link> : <span aria-current="page">{crumb.label}</span>}
                {index < breadcrumbs.length - 1 ? <ChevronRight size={13} aria-hidden="true" /> : null}
              </li>
            ))}
          </ol>
        </nav>
      ) : null}
      <div className="page-header-row">
        <div className="page-header-text">
          <h1 className={mono ? 'mono-title' : undefined}>{title}</h1>
          {description ? <p className="page-description">{description}</p> : null}
          {meta ? <div className="page-meta">{meta}</div> : null}
        </div>
        {actions ? <div className="page-actions">{actions}</div> : null}
      </div>
    </header>
  );
}

/** Heading for a section within a page, with optional description and actions. */
export function SectionHeader({ title, description, actions, as: Heading = 'h2', id }) {
  return (
    <div className="section-header">
      <div>
        <Heading id={id}>{title}</Heading>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="section-actions">{actions}</div> : null}
    </div>
  );
}

export default PageHeader;
