import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';

function compare(a, b) {
  if (a === b) return 0;
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

/**
 * Sortable, paginated table. Search and filters live with the page (it owns the data); this owns ordering.
 * Columns: { key, header, render(row), sortValue?(row), align?, primary?, className? }.
 * The `primary` column links to `rowHref(row)` so every row is reachable by keyboard; on narrow screens rows
 * turn into stacked cards labelled by their column headers.
 */
function DataTable({ columns, rows, rowKey, rowHref, caption, initialSort, pageSize = 20, empty, dense = false }) {
  const navigate = useNavigate();
  const [sort, setSort] = useState(initialSort || null);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const column = sort && columns.find((col) => col.key === sort.key);
    if (!column?.sortValue) return rows;
    const factor = sort.direction === 'desc' ? -1 : 1;
    return [...rows].sort((a, b) => factor * compare(column.sortValue(a), column.sortValue(b)));
  }, [rows, columns, sort]);

  const pageCount = pageSize ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1;
  const currentPage = Math.min(page, pageCount - 1);
  const visible = pageSize ? sorted.slice(currentPage * pageSize, (currentPage + 1) * pageSize) : sorted;

  const toggleSort = (key) => {
    setPage(0);
    setSort((current) =>
      current?.key === key ? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: 'asc' },
    );
  };

  const onRowClick = (event, row) => {
    if (!rowHref || event.target.closest('a, button, input, select, label')) return;
    if (window.getSelection()?.toString()) return; // let people select text without navigating
    navigate(rowHref(row));
  };

  if (!rows.length) return empty || null;

  return (
    <div className={`data-table ${dense ? 'is-dense' : ''}`}>
      <div className="table-scroll">
        <table>
          {caption ? <caption className="visually-hidden">{caption}</caption> : null}
          <thead>
            <tr>
              {columns.map((col) => {
                const active = sort?.key === col.key;
                const ariaSort = active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : undefined;
                const SortIcon = !active ? ArrowUpDown : sort.direction === 'asc' ? ArrowUp : ArrowDown;
                return (
                  <th key={col.key} scope="col" aria-sort={ariaSort} className={`${col.align ? `align-${col.align}` : ''} ${col.className || ''}`}>
                    {col.sortValue ? (
                      <button type="button" className={`sort-button ${active ? 'is-active' : ''}`} onClick={() => toggleSort(col.key)}>
                        {col.header}
                        <SortIcon size={13} aria-hidden="true" />
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={rowKey(row)} className={rowHref ? 'is-clickable' : undefined} onClick={(event) => onRowClick(event, row)}>
                {columns.map((col) => (
                  <td
                    key={col.key}
                    data-label={typeof col.header === 'string' ? col.header : col.key}
                    className={`${col.align ? `align-${col.align}` : ''} ${col.primary ? 'is-primary' : ''} ${col.className || ''}`}
                  >
                    {col.primary && rowHref ? (
                      <Link to={rowHref(row)} className="row-link">
                        {col.render(row)}
                      </Link>
                    ) : (
                      col.render(row)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pageSize && sorted.length > pageSize ? (
        <nav className="pagination" aria-label="Pagination">
          <span className="pagination-summary">
            {currentPage * pageSize + 1}–{Math.min((currentPage + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div className="pagination-controls">
            <button type="button" className="btn btn-secondary btn-sm btn-icon" onClick={() => setPage(currentPage - 1)} disabled={currentPage === 0} aria-label="Previous page">
              <ChevronLeft size={14} aria-hidden="true" />
            </button>
            <span className="pagination-page" aria-current="page">
              Page {currentPage + 1} of {pageCount}
            </span>
            <button type="button" className="btn btn-secondary btn-sm btn-icon" onClick={() => setPage(currentPage + 1)} disabled={currentPage >= pageCount - 1} aria-label="Next page">
              <ChevronRight size={14} aria-hidden="true" />
            </button>
          </div>
        </nav>
      ) : null}
    </div>
  );
}

export default DataTable;
