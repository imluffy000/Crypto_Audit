import { useState } from 'react';
import { Info, Sparkles } from 'lucide-react';
import { scanService } from '../services/scanService';

function ExplanationPanel({ scanId, run, aiAvailable }) {
  const [ai, setAi] = useState(null);
  const [aiState, setAiState] = useState({ loading: false, error: '' });
  const { explanation } = run;

  const requestAi = async () => {
    setAiState({ loading: true, error: '' });
    try {
      setAi(await scanService.requestAiExplanation(scanId, run.candidate_id));
      setAiState({ loading: false, error: '' });
    } catch (error) {
      setAiState({ loading: false, error: error.message });
    }
  };

  return (
    <div className="explanation-panel">
      <p className="explanation-headline">{explanation.headline}</p>

      {explanation.limitations.map((limitation) => (
        <div key={limitation} className="alert-box warning">
          <Info size={15} />
          <div>
            <p>{limitation}</p>
          </div>
        </div>
      ))}

      <div className="explanation-sections">
        {explanation.sections.map((section) => (
          <section key={section.title}>
            <h4>{section.title}</h4>
            <ul>
              {section.points.map((point, index) => (
                <li key={index}>{point}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <div className="ai-explanation">
        {ai ? (
          <>
            <p className="ai-disclaimer">
              <Sparkles size={13} /> {ai.disclaimer} <small>({ai.model})</small>
            </p>
            <p>{ai.text}</p>
          </>
        ) : (
          <button
            type="button"
            className="secondary-button"
            onClick={requestAi}
            disabled={!aiAvailable || aiState.loading || !run.candidate_code}
            title={aiAvailable ? 'Ask the local LLM to explain this evidence in plain language' : 'Requires a local Ollama model'}
          >
            <Sparkles size={14} /> {aiState.loading ? 'Generating…' : 'Explain in plain language (AI)'}
          </button>
        )}
        {aiState.error ? <div className="form-error">{aiState.error}</div> : null}
      </div>
    </div>
  );
}

export default ExplanationPanel;
