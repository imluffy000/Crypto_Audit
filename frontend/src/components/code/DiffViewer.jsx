import { useMemo } from 'react';
import { GitCompareArrows } from 'lucide-react';
import { highlight } from '../../utils/highlight';
import { CodeTokens } from './CodeViewer';

function parseDiff(diff) {
  const rows = [];
  let oldLine = 0;
  let newLine = 0;
  for (const line of diff.split('\n')) {
    if (line.startsWith('---') || line.startsWith('+++')) continue;
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$/.exec(line);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      rows.push({ type: 'hunk', text: line });
    } else if (line.startsWith('-')) {
      rows.push({ type: 'removed', old: oldLine++, text: line.slice(1) });
    } else if (line.startsWith('+')) {
      rows.push({ type: 'added', new: newLine++, text: line.slice(1) });
    } else if (oldLine) {
      rows.push({ type: 'context', old: oldLine++, new: newLine++, text: line.slice(1) });
    }
  }
  return rows;
}

/** Unified diff with old/new line numbers and syntax-highlighted lines. */
function DiffViewer({ diff, path, title = 'Unified diff' }) {
  const rows = useMemo(() => parseDiff(diff || ''), [diff]);
  const stats = rows.reduce((acc, row) => ({ ...acc, [row.type]: (acc[row.type] || 0) + 1 }), {});

  return (
    <figure className="code-viewer">
      <figcaption className="code-header">
        <div className="code-file">
          <GitCompareArrows size={14} aria-hidden="true" />
          <span className="code-title">{title}</span>
          {path ? <span className="code-path mono">{path}</span> : null}
        </div>
        <div className="code-tools">
          <span className="diff-stat added">+{stats.added || 0}</span>
          <span className="diff-stat removed">−{stats.removed || 0}</span>
        </div>
      </figcaption>
      {rows.length ? (
        <div className="code-body is-diff" role="region" tabIndex={0} aria-label="Unified diff">
          {rows.map((row, index) =>
            row.type === 'hunk' ? (
              <div key={index} className="code-row diff-hunk">
                <span className="code-ln" aria-hidden="true" />
                <span className="code-ln" aria-hidden="true" />
                <code className="code-text">{row.text}</code>
              </div>
            ) : (
              <div key={index} className={`code-row ${row.type === 'context' ? '' : `mark-${row.type}`}`}>
                <span className="code-ln" aria-hidden="true">
                  {row.old ?? ''}
                </span>
                <span className="code-ln" aria-hidden="true">
                  {row.new ?? ''}
                </span>
                <span className="code-sign" aria-hidden="true">
                  {row.type === 'added' ? '+' : row.type === 'removed' ? '−' : ''}
                </span>
                <code className="code-text">
                  {row.type !== 'context' ? <span className="visually-hidden">{row.type === 'added' ? 'added: ' : 'removed: '}</span> : null}
                  <CodeTokens tokens={highlight(row.text)[0]} />
                  {row.text ? null : ' '}
                </code>
              </div>
            ),
          )}
        </div>
      ) : (
        <p className="code-empty">No textual change.</p>
      )}
    </figure>
  );
}

export default DiffViewer;
