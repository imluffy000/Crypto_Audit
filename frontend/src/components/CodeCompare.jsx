import { useId, useMemo, useState } from 'react';
import { Columns2, Rows3 } from 'lucide-react';
import { changedLines } from '../utils/diff';
import CodeViewer from './code/CodeViewer';
import DiffViewer from './code/DiffViewer';
import Tabs, { TabPanel } from './ui/Tabs';

/** Original vs repaired candidate, side by side (with changed and flagged lines marked) or as a unified diff. */
function CodeCompare({ original, repaired, diff, path, findingLines = [], findingMarkers = {} }) {
  const [view, setView] = useState('split');
  const tabsId = useId();
  const { removed, added } = useMemo(() => changedLines(diff), [diff]);

  const originalMarks = useMemo(() => {
    const marks = {};
    findingLines.forEach((line) => {
      marks[line] = 'flagged';
    });
    removed.forEach((line) => {
      marks[line] = 'removed';
    });
    return marks;
  }, [findingLines, removed]);

  const repairedMarks = useMemo(() => Object.fromEntries([...added].map((line) => [line, 'added'])), [added]);

  return (
    <div className="code-compare">
      <div className="code-compare-toolbar">
        <Tabs
          idBase={tabsId}
          label="Code view"
          size="sm"
          value={view}
          onChange={setView}
          tabs={[
            { id: 'split', label: 'Side by side', icon: Columns2 },
            { id: 'diff', label: 'Unified diff', icon: Rows3 },
          ]}
        />
        <ul className="code-legend" aria-label="Legend">
          <li><span className="legend-swatch flagged" aria-hidden="true" /> Finding</li>
          <li><span className="legend-swatch removed" aria-hidden="true" /> Removed</li>
          <li><span className="legend-swatch added" aria-hidden="true" /> Added</li>
        </ul>
      </div>
      <TabPanel idBase={tabsId} id={view}>
      {view === 'split' ? (
        <div className="code-split">
          <CodeViewer title="Original" path={path} code={original} marks={originalMarks} markers={findingMarkers} />
          <CodeViewer title="Repaired candidate" path={path} code={repaired} marks={repairedMarks} emptyMessage="This strategy produced no code for this file." />
        </div>
      ) : (
        <DiffViewer diff={diff} path={path} />
      )}
      </TabPanel>
    </div>
  );
}

export default CodeCompare;
