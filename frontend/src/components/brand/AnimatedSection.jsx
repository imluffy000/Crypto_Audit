import { useEffect, useRef, useState } from 'react';

/**
 * A full-height slide that reveals its `.reveal` children (staggered by their `--i`) while it is on
 * screen and gently fades them again when it leaves, so moving between slides feels continuous.
 */
function AnimatedSection({ id, label, className = '', children }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(typeof IntersectionObserver === 'undefined');

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.2 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} id={id} aria-label={label} tabIndex={-1} className={`slide ${visible ? 'is-visible' : ''} ${className}`.trim()}>
      {children}
    </section>
  );
}

export default AnimatedSection;
