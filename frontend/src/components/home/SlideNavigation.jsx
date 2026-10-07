/** Vertical 01–04 slide indicator. The active marker slides between items. */
function SlideNavigation({ slides, active, onSelect }) {
  return (
    <nav className="slide-nav" aria-label="Slides">
      <span className="slide-nav-marker" aria-hidden="true" style={{ '--active': active }} />
      <ol>
        {slides.map((slide, index) => (
          <li key={slide.id}>
            <button
              type="button"
              className={index === active ? 'is-active' : ''}
              aria-label={`${slide.label}, slide ${index + 1} of ${slides.length}`}
              aria-current={index === active ? 'step' : undefined}
              onClick={() => onSelect(index)}
            >
              <span className="slide-nav-label" aria-hidden="true">
                {slide.label}
              </span>
              <span className="slide-nav-num" aria-hidden="true">
                {String(index + 1).padStart(2, '0')}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export default SlideNavigation;
