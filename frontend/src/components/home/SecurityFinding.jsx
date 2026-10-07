import { CheckCircle2 } from 'lucide-react';

/**
 * A sample CryptoAudit finding, laid out like the product's finding view: severity and rule,
 * location and the flagged line, then why it matters, the repair, and the validation outcome.
 */
function SecurityFinding({ className = '', style }) {
  return (
    <article className={`finding-card hover-lift ${className}`.trim()} style={style} aria-label="Example finding: weak randomness">
      <header className="finding-head">
        <span className="finding-severity">
          <span className="finding-severity-dot" aria-hidden="true" />
          High severity
        </span>
        <span className="finding-rule">CR5 · Weak randomness for security tokens</span>
      </header>

      <div className="finding-body">
        <div className="finding-main">
          <h3 className="finding-title">Weak Randomness</h3>
          <p className="finding-location">
            <span>auth/token.py</span>
            <span>Line 42</span>
          </p>
          <pre className="finding-code" aria-label="Flagged code">
            <span className="finding-ln">42</span>
            {'token = str(random.randint(0, 10**12))'}
          </pre>
          <p className="finding-copy">The implementation uses a predictable random source for security-sensitive token generation.</p>
        </div>

        <div className="finding-side">
          <section>
            <h4 className="finding-label">Why it matters</h4>
            <p className="finding-copy">Predictable values can allow attackers to reproduce security-sensitive tokens.</p>
          </section>
          <section>
            <h4 className="finding-label">Recommended repair</h4>
            <p className="finding-copy">Use a cryptographically secure random number generator.</p>
            <pre className="finding-code is-fix" aria-label="Proposed repair">
              <span className="finding-ln">+</span>
              {'token = secrets.token_urlsafe(32)'}
            </pre>
          </section>
        </div>
      </div>

      <footer className="finding-foot">
        <span className="finding-validated">
          <CheckCircle2 size={16} aria-hidden="true" />
          Proposed repair validated
        </span>
        <span className="finding-gates">Re-scan · functional · security gates passed</span>
      </footer>
    </article>
  );
}

export default SecurityFinding;
