/** Bordered surface for a self-contained block of content. Use sparingly; plain sections are often enough. */
function Panel({ title, description, actions, children, flush = false, className = '', as: Tag = 'section', headingLevel = 2, ...rest }) {
  const Heading = `h${headingLevel}`;
  return (
    <Tag className={`panel ${flush ? 'panel-flush' : ''} ${className}`.trim()} {...rest}>
      {title || actions ? (
        <div className="panel-header">
          <div>
            {title ? <Heading className="panel-title">{title}</Heading> : null}
            {description ? <p className="panel-description">{description}</p> : null}
          </div>
          {actions ? <div className="panel-actions">{actions}</div> : null}
        </div>
      ) : null}
      <div className="panel-body">{children}</div>
    </Tag>
  );
}

export default Panel;
