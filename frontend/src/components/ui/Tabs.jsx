import { useId, useRef } from 'react';

/**
 * Accessible tab list (WAI-ARIA tabs pattern): arrow keys / Home / End move between tabs.
 * Render the matching <TabPanel> yourself so panels can hold arbitrary content.
 */
function Tabs({ tabs, value, onChange, label, size = 'md', idBase }) {
  const generated = useId();
  const base = idBase || generated;
  const refs = useRef({});

  const focusTab = (index) => {
    const tab = tabs[(index + tabs.length) % tabs.length];
    onChange(tab.id);
    refs.current[tab.id]?.focus();
  };

  const onKeyDown = (event, index) => {
    if (event.key === 'ArrowRight') focusTab(index + 1);
    else if (event.key === 'ArrowLeft') focusTab(index - 1);
    else if (event.key === 'Home') focusTab(0);
    else if (event.key === 'End') focusTab(tabs.length - 1);
    else return;
    event.preventDefault();
  };

  return (
    <div className={`tabs tabs-${size}`} role="tablist" aria-label={label}>
      {tabs.map((tab, index) => {
        const selected = tab.id === value;
        return (
          <button
            key={tab.id}
            ref={(node) => {
              refs.current[tab.id] = node;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`${base}-panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            className={`tab ${selected ? 'is-active' : ''}`}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {tab.icon ? <tab.icon size={15} aria-hidden="true" /> : null}
            <span>{tab.label}</span>
            {tab.adornment ?? null}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({ idBase, id, children, className = '' }) {
  return (
    <div role="tabpanel" id={`${idBase}-panel-${id}`} aria-labelledby={`${idBase}-tab-${id}`} className={className} tabIndex={0}>
      {children}
    </div>
  );
}

export default Tabs;
