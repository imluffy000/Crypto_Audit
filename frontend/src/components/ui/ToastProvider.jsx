import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { ToastContext } from './toastContext';

const ICONS = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: AlertCircle };
const DURATION_MS = 5000;

function Toast({ toast, onDismiss }) {
  const Icon = ICONS[toast.tone] || Info;
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), DURATION_MS);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div className={`toast toast-${toast.tone}`} role={toast.tone === 'danger' ? 'alert' : 'status'}>
      <Icon size={16} aria-hidden="true" className="toast-icon" />
      <div className="toast-content">
        <p className="toast-title">{toast.title}</p>
        {toast.message ? <p className="toast-message">{toast.message}</p> : null}
      </div>
      <button type="button" className="toast-close" onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification">
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => setToasts((current) => current.filter((toast) => toast.id !== id)), []);
  const notify = useCallback(({ tone = 'info', title, message }) => {
    const id = nextId.current++;
    setToasts((current) => [...current.slice(-3), { id, tone, title, message }]);
  }, []);

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="toast-region" aria-live="polite">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export default ToastProvider;
