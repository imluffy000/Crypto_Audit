import { Link } from 'react-router-dom';
import { ArrowRight, LockKeyhole } from 'lucide-react';
import AnimatedSection from '../brand/AnimatedSection';
import CryptoAuditGraphic from '../brand/CryptoAuditGraphic';
import SecurityFinding from './SecurityFinding';

/** Slide 4: what a result looks like, and the closing call to action. */
function FindingSlide({ id, analyzeTo }) {
  return (
    <AnimatedSection id={id} label="Security finding" className="slide-finding">
      <div className="slide-inner finding-grid">
        <div className="finding-proof">
          <p className="eyebrow reveal" style={{ '--i': 0 }}>
            A real finding
          </p>
          <h2 className="slide-title reveal" style={{ '--i': 1 }}>
            See what your code is hiding.
          </h2>
          <SecurityFinding className="reveal" style={{ '--i': 2 }} />
        </div>

        <aside className="cta-panel reveal" style={{ '--i': 3 }} aria-labelledby="cta-title">
          <div className="cta-copy">
            <h2 id="cta-title" className="cta-title">
              Ready to audit your code?
            </h2>
            <p className="cta-text">Connect a repository and start your first cryptographic security analysis.</p>
            <Link className="brand-btn brand-btn-primary brand-btn-lg" to={analyzeTo}>
              Analyze Your Repository
              <ArrowRight size={18} className="btn-arrow" aria-hidden="true" />
            </Link>
            <p className="trust-note">
              <LockKeyhole size={14} aria-hidden="true" />
              Read-only access · No code execution
            </p>
          </div>
          <CryptoAuditGraphic compact className="cta-graphic" />
        </aside>
      </div>
    </AnimatedSection>
  );
}

export default FindingSlide;
