import { useState } from 'react';
import { MessageSquareText } from 'lucide-react';
import { scanService } from '../services/scanService';
import Badge from './ui/Badge';
import Button from './ui/Button';
import { Alert } from './ui/States';
import { useToast } from './ui/toastContext';

// The evidence explanation arrives as plain sentences (backend reporting/explanation.py). These patterns
// let each kind of sentence be laid out as a compact row; anything else is shown as written.
const FOUND = /^Line (\d+) \[([^\]·]+?)(?: · [^\]]+)?\]: (.*?)(?: Guidance: (.*))?$/;
const NOTE_LINE = /^line (\d+) \[([^\]]+)\]: (.*)$/;
const GATE = /^(V\d) \(([^)]+)\): ([A-Z_]+) - (.*)$/;
const CHECK = /^\s+(V\d) check '([^']+)' ([A-Z_]+): (.*)$/;
const LINES_CHANGED = /^(\d+) line\(s\) added, (\d+) line\(s\) removed\.$/;
const CALLS = /^(Stopped calling|Now calls): (.*)$/;
const REASON = /^(V\d) ([A-Z_]+): (.*)$/;

const STATUS_TONE = {
  PASS: 'success',
  FAIL: 'danger',
  ERROR: 'danger',
  NOT_RUN: 'neutral',
  NOT_APPLICABLE: 'neutral',
};

function StatusBadge({ status }) {
  return <Badge tone={STATUS_TONE[status] || 'neutral'}>{status.replace(/_/g, ' ').toLowerCase()}</Badge>;
}

function FoundSection({ points }) {
  const rows = points.map((point) => point.match(FOUND));
  const guidance = [
    ...new Set(
      rows
        .filter(Boolean)
        .map((m) => m[4])
        .filter(Boolean),
    ),
  ];
  return (
    <>
      <ul className="why-rows">
        {points.map((point, index) => {
          const m = rows[index];
          if (!m) return <li key={index}>{point}</li>;
          return (
            <li key={index}>
              <span className="why-tags">
                <span className="why-line">Line {m[1]}</span>
                <span className="why-rule mono">{m[2].trim()}</span>
              </span>
              <span>{m[3]}</span>
            </li>
          );
        })}
      </ul>
      {guidance.map((text) => (
        <p key={text} className="why-note">
          <strong className="text-strong">How to fix.</strong> {text}
        </p>
      ))}
    </>
  );
}

function ChangeSection({ points }) {
  const stats = [];
  const calls = [];
  const notes = [];
  const other = [];
  points.forEach((point) => {
    const lines = point.match(LINES_CHANGED);
    const call = point.match(CALLS);
    if (lines) stats.push(lines);
    else if (call) calls.push(call);
    else if (point.startsWith('Strategy note: ')) notes.push(point.slice('Strategy note: '.length));
    else other.push(point);
  });

  return (
    <>
      {stats.length || calls.length ? (
        <div className="why-change">
          {stats.map((m, index) => (
            <span key={index} className="why-diffstat">
              <span className="added">+{m[1]}</span>
              <span className="removed">−{m[2]}</span>
              <span className="muted">lines</span>
            </span>
          ))}
          {calls.map((m) => (
            <span key={m[1]} className="why-calls">
              <span className="muted">{m[1]}</span>
              {m[2].split(', ').map((api) => (
                <code key={api} className="why-api">
                  {api}
                </code>
              ))}
            </span>
          ))}
        </div>
      ) : null}
      {other.map((point) => (
        <p key={point}>{point}</p>
      ))}
      {notes.length ? (
        <ul className="why-rows why-notes">
          {notes.map((note, index) => {
            const m = note.match(NOTE_LINE);
            return (
              <li key={index}>
                {m ? (
                  <>
                    <span className="why-tags">
                      <span className="why-line">Line {m[1]}</span>
                      <span className="why-rule mono">{m[2]}</span>
                    </span>
                    <span className="mono small">{m[3]}</span>
                  </>
                ) : (
                  <span className="mono small">{note}</span>
                )}
              </li>
            );
          })}
        </ul>
      ) : null}
    </>
  );
}

function EvidenceSection({ points }) {
  return (
    <ul className="why-rows">
      {points.map((point, index) => {
        const gate = point.match(GATE);
        const check = point.match(CHECK);
        if (gate) {
          return (
            <li key={index}>
              <span className="why-tags">
                <span className="why-gate mono">{gate[1]}</span>
                <StatusBadge status={gate[3]} />
              </span>
              <span>
                {gate[4]} <span className="muted small">({gate[2]})</span>
              </span>
            </li>
          );
        }
        if (check) {
          return (
            <li key={index} className="why-check">
              <span className="why-tags">
                <StatusBadge status={check[3]} />
              </span>
              <span>
                <span className="mono small">{check[2]}</span> · {check[4]}
              </span>
            </li>
          );
        }
        return <li key={index}>{point.trim()}</li>;
      })}
    </ul>
  );
}

function PlainSection({ points }) {
  return (
    <ul className="why-rows">
      {points.map((point, index) => {
        const reason = point.match(REASON);
        if (!reason)
          return (
            <li key={index} className="why-plain-row">
              {point}
            </li>
          );
        return (
          <li key={index}>
            <span className="why-tags">
              <span className="why-gate mono">{reason[1]}</span>
              <StatusBadge status={reason[2]} />
            </span>
            <span>{reason[3]}</span>
          </li>
        );
      })}
    </ul>
  );
}

function sectionBody(section) {
  if (section.title === 'What CryptoAudit found') return <FoundSection points={section.points} />;
  if (/^What .+ changed$/.test(section.title)) return <ChangeSection points={section.points} />;
  if (section.title === 'Validation evidence') return <EvidenceSection points={section.points} />;
  return <PlainSection points={section.points} />;
}

/**
 * Evidence-based "why" for a candidate. The optional AI text only rephrases this evidence; it is labelled
 * as such and never changes the verdict.
 */
function ExplanationPanel({ scanId, run, aiAvailable }) {
  const notify = useToast();
  const [ai, setAi] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { explanation } = run;

  const requestAi = async () => {
    setLoading(true);
    setError('');
    try {
      setAi(await scanService.requestAiExplanation(scanId, run.candidate_id));
      notify({
        tone: 'success',
        title: 'Summary ready',
        message: 'Written by a language model from the evidence; the verdict is unchanged.',
      });
    } catch (err) {
      setError(err.message);
      notify({
        tone: 'danger',
        title: 'Summary could not be written',
        message: err.message,
      });
    } finally {
      setLoading(false);
    }
  };

  const disabledReason = !run.candidate_code
    ? 'There is no candidate code to explain.'
    : !aiAvailable
      ? 'Needs a language model: start Ollama or set an OpenRouter key on the server.'
      : '';

  return (
    <div className="explanation">
      <p className="explanation-headline">{explanation.headline}</p>

      {explanation.limitations.length ? (
        <Alert tone="warning" title="Limitations">
          {explanation.limitations.length === 1 ? (
            explanation.limitations[0]
          ) : (
            <ul className="bullet-list">
              {explanation.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          )}
        </Alert>
      ) : null}

      {explanation.sections
        .filter((section) => section.points.length)
        .map((section) => (
          <div key={section.title} className="explanation-section">
            <h4>{section.title}</h4>
            {sectionBody(section)}
          </div>
        ))}

      <div className="ai-explanation">
        {ai ? (
          <>
            <p className="ai-label">
              <MessageSquareText size={14} aria-hidden="true" /> Plain-language summary · <span className="mono">{ai.model}</span>
            </p>
            <p className="ai-text">{ai.text}</p>
            <p className="ai-disclaimer">{ai.disclaimer}</p>
          </>
        ) : (
          <div className="ai-request">
            <Button size="sm" icon={MessageSquareText} onClick={requestAi} loading={loading} disabled={Boolean(disabledReason)}>
              {loading ? 'Writing summary…' : 'Summarise in plain language'}
            </Button>
            <p className="muted small">
              {disabledReason || 'Generated by a language model from the evidence above. It does not affect the verdict.'}
            </p>
          </div>
        )}
        {error ? (
          <Alert tone="danger" title="Summary could not be written" className="ai-error">
            {error}
          </Alert>
        ) : null}
      </div>
    </div>
  );
}

export default ExplanationPanel;
