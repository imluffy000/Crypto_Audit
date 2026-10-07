import { useId } from 'react';
import { Search, X } from 'lucide-react';

export function SearchBar({ value, onChange, placeholder = 'Search', label = 'Search', className = '' }) {
  const id = useId();
  return (
    <div className={`search-bar ${className}`.trim()}>
      <label htmlFor={id} className="visually-hidden">
        {label}
      </label>
      <Search size={15} aria-hidden="true" className="search-icon" />
      <input id={id} type="search" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} autoComplete="off" />
      {value ? (
        <button type="button" className="search-clear" onClick={() => onChange('')} aria-label="Clear search">
          <X size={14} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}

export function Select({ label, value, onChange, options, hideLabel = true, className = '' }) {
  const id = useId();
  return (
    <div className={`select ${className}`.trim()}>
      <label htmlFor={id} className={hideLabel ? 'visually-hidden' : 'field-label'}>
        {label}
      </label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Row of search + select filters above a list or table. */
function FilterBar({ children, summary }) {
  return (
    <div className="filter-bar">
      <div className="filter-controls">{children}</div>
      {summary ? <p className="filter-summary">{summary}</p> : null}
    </div>
  );
}

export default FilterBar;
