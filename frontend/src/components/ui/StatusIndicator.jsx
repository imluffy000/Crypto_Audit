const SCAN_STATUS = {
  COMPLETED: { tone: 'success', label: 'Completed' },
  FAILED: { tone: 'danger', label: 'Failed' },
  RUNNING: { tone: 'info', label: 'Running' },
  QUEUED: { tone: 'neutral', label: 'Queued' },
};

/** Dot + label for a scan's lifecycle status. Running scans pulse (unless reduced motion is requested). */
function StatusIndicator({ status, label }) {
  const meta = SCAN_STATUS[status] || { tone: 'neutral', label: status ? status.toLowerCase() : 'Unknown' };
  return (
    <span className={`status-indicator tone-${meta.tone} ${status === 'RUNNING' ? 'is-live' : ''}`}>
      <span className="status-dot" aria-hidden="true" />
      {label || meta.label}
    </span>
  );
}

export default StatusIndicator;
