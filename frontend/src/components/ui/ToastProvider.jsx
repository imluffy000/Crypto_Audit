import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { ToastContext } from './toastContext';

const ICONS = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: AlertCircle };
// Errors stay longer so there is time to read them; hovering or focusing a toast pauses it.
const DURATION_MS = { info: 4000, success: 4000, warning: 7000, danger: 9000 };
const MAX_TOASTS = 4;
const MAX_MESSAGE = 240;

function Toast({ toast, onDismiss }) {
  const Icon = ICONS[toast.tone] || Info;
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return undefined;
    const timer = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, paused, onDismiss]);

  return (
    <div
      className={`toast toast-${toast.tone}`}
      role={toast.tone === 'danger' ? 'alert' : 'status'}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <Icon size={16} aria-hidden="true" className="toast-icon" />
      <div className="toast-content">
        <p className="toast-title">
          {toast.title}
          {toast.count > 1 ? <span className="toast-count"> ×{toast.count}</span> : null}
        </p>
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

  const notify = useCallback(({ tone = 'info', title, message, duration }) => {
    const text = message && message.length > MAX_MESSAGE ? `${message.slice(0, MAX_MESSAGE - 1)}…` : message;
    setToasts((current) => {
      // The same notification twice in a row (e.g. a retried request) is counted, not stacked.
      const same = current.find((toast) => toast.tone === tone && toast.title === title && toast.message === text);
      if (same) {
        return current.map((toast) => (toast === same ? { ...toast, count: toast.count + 1, id: nextId.current++ } : toast));
      }
      const toast = { id: nextId.current++, tone, title, message: text, count: 1, duration: duration || DURATION_MS[tone] || 5000 };
      return [...current.slice(-(MAX_TOASTS - 1)), toast];
    });
  }, []);

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="toast-region" aria-live="polite" aria-label="Notifications">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export default ToastProvider;
