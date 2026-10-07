import AnimatedSection from '../brand/AnimatedSection';

const CAPABILITIES = [
  {
    title: 'Cryptographic misuse',
    text: 'Detect inappropriate or unsafe use of cryptographic libraries and APIs.',
    sample: 'hashlib.md5(password)',
  },
  {
    title: 'Weak implementations',
    text: 'Identify weak algorithms, insecure randomness, unsafe configurations, and risky patterns.',
    sample: 'AES.new(key, AES.MODE_ECB)',
  },
  {
    title: 'Codebase context',
    text: 'Understand surrounding code so findings are not based only on isolated lines.',
    sample: '3 call sites · 2 modules',
  },
  {
    title: 'AI-assisted reasoning',
    text: 'Explain why an issue matters and provide contextual repair recommendations.',
    sample: 'why it matters → repair',
  },
];

/** Slide 2: what CryptoAudit finds, as one connected panel of four capabilities. */
function CapabilitySlide({ id }) {
  return (
    <AnimatedSection id={id} label="Detection" className="slide-capabilities">
      <div className="slide-inner">
        <header className="slide-head">
          <div>
            <p className="eyebrow reveal" style={{ '--i': 0 }}>
              What it finds
            </p>
            <h2 className="slide-title reveal" style={{ '--i': 1 }}>
              Cryptography can fail without looking broken.
            </h2>
          </div>
          <p className="slide-lead reveal" style={{ '--i': 2 }}>
            CryptoAudit checks how cryptography is used, not just whether it runs.
          </p>
        </header>

        <ol className="capability-grid">
          {CAPABILITIES.map((item, index) => (
            <li key={item.title} className={`capability capability-${index + 1} reveal`} style={{ '--i': index + 3 }}>
              <span className="capability-index" aria-hidden="true">
                {String(index + 1).padStart(2, '0')}
              </span>
              <div className="capability-body">
                <h3 className="capability-title">{item.title}</h3>
                <p className="capability-text">{item.text}</p>
              </div>
              <code className="capability-sample" aria-hidden="true">
                {item.sample}
              </code>
            </li>
          ))}
        </ol>
      </div>
    </AnimatedSection>
  );
}

export default CapabilitySlide;
