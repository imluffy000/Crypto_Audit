import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AppContext';
import CryptoAuditNavbar from '../components/home/CryptoAuditNavbar';
import SlideNavigation from '../components/home/SlideNavigation';
import HeroSlide from '../components/home/HeroSlide';
import CapabilitySlide from '../components/home/CapabilitySlide';
import WorkflowSlide from '../components/home/WorkflowSlide';
import FindingSlide from '../components/home/FindingSlide';

const SLIDES = [
  { id: 'slide-overview', label: 'Overview' },
  { id: 'slide-detection', label: 'Detection' },
  { id: 'slide-workflow', label: 'How it works' },
  { id: 'slide-security', label: 'Security' },
];

const NAV_LINKS = [
  { label: 'How It Works', index: 2 },
  { label: 'Detection', index: 1 },
  { label: 'Security', index: 3 },
];

// Slide-by-slide behaviour (snapping, arrow keys) only applies where every slide fits the screen.
const SNAP_QUERY = '(min-width: 901px) and (min-height: 640px)';

const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** / — the public four-slide landing page. */
function Home() {
  const { user } = useAuth();
  const [active, setActive] = useState(0);
  const activeRef = useRef(0);

  const analyzeTo = user ? '/repositories/github' : '/login';

  const goTo = useCallback((index) => {
    const target = Math.max(0, Math.min(SLIDES.length - 1, index));
    const slide = document.getElementById(SLIDES[target].id);
    if (!slide) return;
    slide.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
    slide.focus({ preventScroll: true });
  }, []);

  // Scroll snapping lives on the document, so wheel, trackpad, touch and keyboard scrolling stay native.
  useEffect(() => {
    const root = document.documentElement;
    root.classList.add('home-snap');
    return () => root.classList.remove('home-snap');
  }, []);

  // The slide covering most of the viewport is the active one.
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const index = SLIDES.findIndex((slide) => slide.id === entry.target.id);
          activeRef.current = index;
          setActive(index);
        });
      },
      { threshold: 0.55 },
    );
    SLIDES.forEach((slide) => {
      const node = document.getElementById(slide.id);
      if (node) observer.observe(node);
    });
    return () => observer.disconnect();
  }, []);

  // Arrow Down / Up move one slide, but only on screens where slides fit and focus is not in a field.
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.target.closest?.('input, textarea, select, [contenteditable="true"], [role="listbox"], [role="menu"]')) return;
      if (!window.matchMedia(SNAP_QUERY).matches) return;
      event.preventDefault();
      goTo(activeRef.current + (event.key === 'ArrowDown' ? 1 : -1));
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [goTo]);

  return (
    <div className="brand-page home">
      <CryptoAuditNavbar
        links={NAV_LINKS}
        active={active}
        onNavigate={goTo}
        signInTo={user ? '/dashboard' : '/login'}
        signInLabel={user ? 'Dashboard' : 'Sign In'}
        analyzeTo={analyzeTo}
      />
      <main className="home-slides page-anim">
        <HeroSlide id={SLIDES[0].id} analyzeTo={analyzeTo} onHowItWorks={() => goTo(2)} />
        <CapabilitySlide id={SLIDES[1].id} />
        <WorkflowSlide id={SLIDES[2].id} />
        <FindingSlide id={SLIDES[3].id} analyzeTo={analyzeTo} />
      </main>
      <SlideNavigation slides={SLIDES} active={active} onSelect={goTo} />
    </div>
  );
}

export default Home;
