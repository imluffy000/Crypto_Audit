// Presentation helpers shared by pages: ordering, dates and labels. No data is invented here.

export const SEVERITY_ORDER = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
export const VERDICT_ORDER = { VERIFIED: 4, UNVERIFIED: 3, FAILED: 2, NO_CANDIDATE: 1 };

export const RULE_NAMES = {
  CR1: 'Weak hashing for stored credentials',
  CR2: 'Weak or unauthenticated encryption mode',
  CR3: 'Static or reused IV / nonce',
  CR4: 'Weak KDF parameters or static salt',
  CR5: 'Weak randomness for security tokens',
};

export function formatDateTime(iso) {
  if (!iso) return '–';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '–';
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatRelative(iso) {
  if (!iso) return '–';
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (Number.isNaN(seconds)) return '–';
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} d ago`;
  return new Date(iso).toLocaleDateString();
}

export function formatMegabytes(bytes) {
  if (!bytes) return '–';
  const mb = bytes / (1024 * 1024);
  return mb < 0.1 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${mb.toFixed(1)} MB`;
}

export function humanize(value = '') {
  const text = value.replaceAll('_', ' ').toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}
