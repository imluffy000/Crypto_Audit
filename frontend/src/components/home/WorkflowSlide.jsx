import { Lightbulb, Network, ScanSearch } from 'lucide-react';
import AnimatedSection from '../brand/AnimatedSection';
import { GitHubMark } from '../auth/GithubAuthButton';

function GitHubIcon() {
  return <GitHubMark size={20} />;
}

const STAGES = [
  { title: 'Connect', text: 'Connect your GitHub repository.', output: 'github.com/acme/payments', icon: GitHubIcon },
  { title: 'Understand', text: 'Parse the repository and build context around the code.', output: '412 modules · call graph', icon: Network },
  { title: 'Analyze', text: 'Apply cryptographic security analysis and detect potential misuse.', output: 'CR1–CR5 rules', icon: ScanSearch },
  { title: 'Explain & recommend', text: 'Use contextual AI reasoning to explain the issue and suggest a repair.', output: 'explanation + repair', icon: Lightbulb },
];

/** Slide 3: the four-stage pipeline. Stages and their connecting lines reveal in sequence. */
function WorkflowSlide({ id }) {
  return (
    <AnimatedSection id={id} label="How it works" className="slide-workflow">
      <div className="slide-inner">
        <header className="slide-head">
          <div>
            <p className="eyebrow reveal" style={{ '--i': 0 }}>
              How it works
            </p>
            <h2 className="slide-title reveal" style={{ '--i': 1 }}>
              From codebase to actionable finding.
            </h2>
          </div>
        </header>

        <ol className="pipeline">
          {STAGES.map(({ title, text, output, icon: Icon }, index) => (
            <li key={title} className="flow reveal" style={{ '--i': index * 2 + 2 }}>
              <div className="flow-rail">
                <span className="flow-node">
                  <Icon size={20} aria-hidden="true" />
                </span>
                {index < STAGES.length - 1 ? (
                  <span className="flow-link" aria-hidden="true">
                    <span className="flow-link-fill" />
                    <span className="flow-link-dot" />
                  </span>
                ) : null}
              </div>
              <div className="flow-card hover-lift">
                <span className="flow-index">{String(index + 1).padStart(2, '0')}</span>
                <h3 className="flow-title">{title}</h3>
                <p className="flow-text">{text}</p>
                <code className="flow-output" aria-hidden="true">
                  {output}
                </code>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </AnimatedSection>
  );
}

export default WorkflowSlide;
