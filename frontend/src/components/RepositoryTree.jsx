import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, FileText, Folder, FolderOpen } from 'lucide-react';
import { formatFileSize } from '../utils/fileUtils';

// Keep a node if it matches the search/extension filter or if any descendant does.
function filterTree(node, term, extension) {
  if (node.type !== 'folder') {
    const nameOk = !term || node.name.toLowerCase().includes(term);
    const extOk = extension === 'all' || node.fileType === extension;
    return nameOk && extOk ? node : null;
  }
  const children = (node.children || []).map((child) => filterTree(child, term, extension)).filter(Boolean);
  const folderNameMatches = term && extension === 'all' && node.name.toLowerCase().includes(term);
  if (!children.length && !folderNameMatches) return null;
  return { ...node, children: folderNameMatches && !children.length ? node.children : children };
}

function sortChildren(children = []) {
  return [...children].sort((a, b) => (a.type === b.type ? a.name.localeCompare(b.name) : a.type === 'folder' ? -1 : 1));
}

/** File tree with expand/collapse. While searching, every folder on a matching path is opened. */
function RepositoryTree({ tree, searchQuery = '', extensionFilter = 'all' }) {
  const [collapsed, setCollapsed] = useState(() => new Set());
  const term = searchQuery.trim().toLowerCase();
  const filtering = Boolean(term) || extensionFilter !== 'all';

  const visible = useMemo(() => (tree ? filterTree(tree, term, extensionFilter) : null), [tree, term, extensionFilter]);

  if (!visible || (visible.type === 'folder' && !visible.children?.length)) {
    return <p className="tree-empty">{filtering ? 'No files match the current search or filter.' : 'This repository has no files to show.'}</p>;
  }

  const toggle = (path) =>
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const renderNode = (node, depth, path) => {
    const isFolder = node.type === 'folder';
    const open = filtering || !collapsed.has(path);
    const indent = { paddingLeft: `${depth * 16 + 8}px` };

    if (!isFolder) {
      return (
        <li key={path} role="treeitem" aria-selected={false} className="tree-row tree-file" style={indent}>
          <FileText size={14} aria-hidden="true" className="tree-icon" />
          <span className="tree-name mono">{node.name}</span>
          <span className="tree-meta">{formatFileSize(node.size || 0)}</span>
        </li>
      );
    }

    return (
      <li key={path} role="treeitem" aria-expanded={open} aria-selected={false}>
        <button type="button" className="tree-row tree-folder" style={indent} onClick={() => toggle(path)} disabled={filtering}>
          {open ? <ChevronDown size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
          {open ? <FolderOpen size={14} aria-hidden="true" className="tree-icon" /> : <Folder size={14} aria-hidden="true" className="tree-icon" />}
          <span className="tree-name mono">{node.name}</span>
          <span className="tree-meta">{(node.children || []).length}</span>
        </button>
        {open ? (
          <ul role="group">{sortChildren(node.children).map((child) => renderNode(child, depth + 1, `${path}/${child.name}`))}</ul>
        ) : null}
      </li>
    );
  };

  return (
    <ul className="repo-tree" role="tree" aria-label="Repository files">
      {renderNode(visible, 0, visible.name || 'repository')}
    </ul>
  );
}

export default RepositoryTree;
