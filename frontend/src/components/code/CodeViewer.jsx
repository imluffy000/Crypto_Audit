import { useMemo, useState } from 'react';
import { Check, Copy, FileCode2, FoldVertical, UnfoldVertical } from 'lucide-react';
import { highlight, LANGUAGE_LABELS, languageFromPath } from '../../utils/highlight';
import { useToast } from '../ui/toastContext';

const MARK_SIGNS = { added: '+', removed: '−', flagged: '!' };

export function CodeTokens({ tokens }) {
  return tokens.map((token, index) =>
    token.type === 'plain' ? token.text : (
      <span key={index} className={`tok-${token.type}`}>
        {token.text}
      </span>
    ),
  );
}

function visibleSegments(lineCount, marked, context) {
  if (!marked.length) return [{ start: 1, end: lineCount, hidden: false }];
  const keep = new Array(lineCount + 2).fill(false);
  marked.forEach((line) => {
    for (let n = Math.max(1, line - context); n <= Math.min(lineCount, line + context); n += 1) keep[n] = true;
  });
  const segments = [];
  let start = 1;
  for (let n = 2; n <= lineCount + 1; n += 1) {
    if (n === lineCount + 1 || keep[n] !== keep[start]) {
      segments.push({ start, end: n - 1, hidden: !keep[start] });
      start = n;
    }
  }
  return segments;
}

/**
 * Read-only code view: file path, language, line numbers, syntax highlighting, highlighted lines and
 * finding markers. Long files collapse to the marked lines plus context; hidden runs can be expanded.
 *
 * marks:   { [line]: 'added' | 'removed' | 'flagged' }
 * markers: { [line]: [{ label, tone }] } — badges shown at the end of a line (e.g. the rule that fired).
 */
function CodeViewer({ code, path, title, language, marks = {}, markers = {}, context = 4, collapsible = true, emptyMessage = 'No code.' }) {
  const notify = useToast();
  const lang = language || languageFromPath(path);
  const lines = useMemo(() => highlight(code || '', lang), [code, lang]);
  const markedLines = useMemo(
    () => [...new Set([...Object.keys(marks), ...Object.keys(markers)].map(Number))].sort((a, b) => a - b),
    [marks, markers],
  );
  const canCollapse = collapsible && markedLines.length > 0 && lines.length > markedLines.length + context * 4;
  const [collapsed, setCollapsed] = useState(true);
  const [expanded, setExpanded] = useState(() => new Set());
  const [copied, setCopied] = useState(false);

  const segments = useMemo(
    () => (canCollapse && collapsed ? visibleSegments(lines.length, markedLines, context) : [{ start: 1, end: lines.length, hidden: false }]),
    [canCollapse, collapsed, lines.length, markedLines, context],
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      notify({ tone: 'danger', title: 'Could not copy', message: 'Clipboard access was blocked by the browser.' });
    }
  };

  const renderLine = (number) => {
    const mark = marks[number];
    return (
      <div key={number} className={`code-row ${mark ? `mark-${mark}` : ''}`}>
        <span className="code-ln" aria-hidden="true">
          {number}
        </span>
        <span className="code-sign" aria-hidden="true">
          {MARK_SIGNS[mark] || ''}
        </span>
        <code className="code-text">
          {mark ? <span className="visually-hidden">{`${mark} line ${number}: `}</span> : null}
          <CodeTokens tokens={lines[number - 1]} />
          {lines[number - 1].length === 0 ? ' ' : null}
          {(markers[number] || []).map((marker) => (
            <span key={marker.label} className={`code-marker tone-${marker.tone || 'warning'}`}>
              {marker.label}
            </span>
          ))}
        </code>
      </div>
    );
  };

  return (
    <figure className="code-viewer">
      <figcaption className="code-header">
        <div className="code-file">
          <FileCode2 size={14} aria-hidden="true" />
          {title ? <span className="code-title">{title}</span> : null}
          {path ? <span className="code-path mono">{path}</span> : null}
        </div>
        <div className="code-tools">
          <span className="code-lang">{LANGUAGE_LABELS[lang] || lang}</span>
          {canCollapse ? (
            <button type="button" className="code-tool" onClick={() => setCollapsed((value) => !value)} aria-pressed={!collapsed}>
              {collapsed ? <UnfoldVertical size={14} aria-hidden="true" /> : <FoldVertical size={14} aria-hidden="true" />}
              {collapsed ? 'Full file' : 'Changes only'}
            </button>
          ) : null}
          {code ? (
            <button type="button" className="code-tool" onClick={copy} aria-label="Copy code">
              {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
              <span className="code-tool-label">{copied ? 'Copied' : 'Copy'}</span>
            </button>
          ) : null}
        </div>
      </figcaption>
      {code ? (
        <div className="code-body" role="region" tabIndex={0} aria-label={title ? `${title} code` : 'Code'}>
          {segments.map((segment) => {
            const key = `${segment.start}-${segment.end}`;
            if (segment.hidden && !expanded.has(key)) {
              const count = segment.end - segment.start + 1;
              return (
                <button key={key} type="button" className="code-fold" onClick={() => setExpanded((set) => new Set(set).add(key))}>
                  <UnfoldVertical size={13} aria-hidden="true" />
                  Show {count} hidden {count === 1 ? 'line' : 'lines'} ({segment.start}–{segment.end})
                </button>
              );
            }
            return Array.from({ length: segment.end - segment.start + 1 }, (_, i) => renderLine(segment.start + i));
          })}
        </div>
      ) : (
        <p className="code-empty">{emptyMessage}</p>
      )}
    </figure>
  );
}

export default CodeViewer;
