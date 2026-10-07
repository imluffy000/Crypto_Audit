import { useMemo, useState } from 'react';
import { changedLines } from '../utils/diff';

function CodePane({ title, code, marks }) {
  const lines = (code || '').replace(/\n$/, '').split('\n');
  return (
    <div className="code-pane">
      <div className="code-pane-title">{title}</div>
      <pre>
        {lines.map((text, index) => {
          const number = index + 1;
          return (
            <div key={number} className={`code-line ${marks(number)}`}>
              <span className="line-number">{number}</span>
              <code>{text || ' '}</code>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

function CodeCompare({ original, repaired, diff, findingLines = [] }) {
  const [view, setView] = useState('split');
  const { removed, added } = useMemo(() => changedLines(diff), [diff]);
  const flagged = useMemo(() => new Set(findingLines), [findingLines]);

  return (
    <div className="code-compare">
      <div className="tab-row compact">
        <button type="button" className={`tab-button ${view === 'split' ? 'active' : ''}`} onClick={() => setView('split')}>
          Side by side
        </button>
        <button type="button" className={`tab-button ${view === 'diff' ? 'active' : ''}`} onClick={() => setView('diff')}>
          Unified diff
        </button>
      </div>
      {view === 'split' ? (
        <div className="code-split">
          <CodePane
            title="Original"
            code={original}
            marks={(n) => [removed.has(n) ? 'removed' : '', flagged.has(n) ? 'flagged' : ''].join(' ')}
          />
          {repaired ? (
            <CodePane title="Repaired candidate" code={repaired} marks={(n) => (added.has(n) ? 'added' : '')} />
          ) : (
            <div className="code-pane empty">This strategy produced no code.</div>
          )}
        </div>
      ) : (
        <pre className="unified-diff">
          {(diff || 'No textual change.').split('\n').map((line, index) => (
            <div
              key={index}
              className={line.startsWith('+') && !line.startsWith('+++') ? 'added' : line.startsWith('-') && !line.startsWith('---') ? 'removed' : ''}
            >
              {line || ' '}
            </div>
          ))}
        </pre>
      )}
    </div>
  );
}

export default CodeCompare;
