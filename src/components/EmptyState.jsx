function EmptyState({ title, description, actionText, onAction }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">◌</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {actionText ? (
        <button type="button" className="primary-button" onClick={onAction}>
          {actionText}
        </button>
      ) : null}
    </div>
  );
}

export default EmptyState;
