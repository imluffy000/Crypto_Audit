import { Link } from 'react-router-dom';
import { ArrowRight, LockKeyhole } from 'lucide-react';
import AnimatedSection from '../brand/AnimatedSection';
import AlgorithmBadge from '../brand/AlgorithmBadge';
import AnalysisCard from '../brand/AnalysisCard';
import CryptoAuditGraphic from '../brand/CryptoAuditGraphic';

/** Slide 1: what CryptoAudit is, the main call to action, and the brand artwork. */
function HeroSlide({ id, analyzeTo, onHowItWorks }) {
  return (
    <AnimatedSection id={id} label="Overview" className="slide-hero">
      <div className="slide-inner hero-grid">
        <div className="hero-copy">
          <p className="eyebrow reveal" style={{ '--i': 0 }}>
            Cryptographic security analysis
          </p>
          <h1 className="hero-title reveal" style={{ '--i': 1 }}>
            Find the cryptographic <span className="title-mark">weaknesses</span> hiding in your code.
          </h1>
          <p className="hero-lead reveal" style={{ '--i': 2 }}>
            CryptoAudit analyzes your repositories for cryptographic misuse, insecure implementations, and risky patterns — then explains
            the issue and recommends how to fix it.
          </p>
          <div className="hero-actions reveal" style={{ '--i': 3 }}>
            <Link className="brand-btn brand-btn-primary brand-btn-lg" to={analyzeTo}>
              Analyze Your Repository
              <ArrowRight size={18} className="btn-arrow" aria-hidden="true" />
            </Link>
            <button type="button" className="brand-btn brand-btn-secondary brand-btn-lg" onClick={onHowItWorks}>
              See How It Works
            </button>
          </div>
          <p className="trust-note reveal" style={{ '--i': 4 }}>
            <LockKeyhole size={14} aria-hidden="true" />
            Read-only analysis · Your code is never executed
          </p>
        </div>

        <div className="hero-visual reveal" style={{ '--i': 2 }}>
          <CryptoAuditGraphic className="hero-graphic">
            <AlgorithmBadge name="AES-256" className="graphic-float pos-aes" style={{ '--rise-delay': '500ms' }} />
            <AlgorithmBadge name="SHA-256" className="graphic-float pos-sha" style={{ '--rise-delay': '650ms', '--float-delay': '-2s' }} />
            <AnalysisCard
              className="graphic-float pos-issues"
              style={{ '--rise-delay': '800ms', '--float-delay': '-3.5s' }}
              eyebrow="Crypto scan"
              title="23 issues found"
              detail="127 files · CR1–CR5"
              status={{ tone: 'live', caption: 'Status', label: 'Analysis complete' }}
            />
            <AnalysisCard className="graphic-float pos-static" style={{ '--rise-delay': '950ms', '--float-delay': '-1s' }} eyebrow="Static analysis" detail="auth/token.py">
              <span className="scan-track" />
            </AnalysisCard>
            <AlgorithmBadge name="Weak RNG" tone="warning" className="graphic-float pos-rng" style={{ '--rise-delay': '1100ms', '--float-delay': '-4.5s' }} />
          </CryptoAuditGraphic>
        </div>
      </div>
    </AnimatedSection>
  );
}

export default HeroSlide;
