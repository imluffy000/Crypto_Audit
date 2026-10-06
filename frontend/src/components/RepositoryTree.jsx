import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, FileText, FolderClosed, FolderOpen } from 'lucide-react';
import { formatFileSize } from '../utils/fileUtils';

function buildMatches(node, term, extensionFilter) {
  if (!node) return false;

  const title = (node.name || '').toLowerCase();
  const searchMatches = !term || title.includes(term.toLowerCase());
  const extensionMatches = extensionFilter === 'all' || node.fileType === extensionFilter;
  return searchMatches && extensionMatches;
}

function RepositoryTree({ tree, searchQuery = '', extensionFilter = 'all' }) {
  const [expandedFolders, setExpandedFolders] = useState({ repository: true });

  const visibleTree = useMemo(() => {
    if (!tree) return null;

    const walk = (node, parentPath = 'repository') => {
      if (!node) return null;

      const isFolder = node.type === 'folder';
      const matches = buildMatches(node, searchQuery, extensionFilter);
      const childMatches = isFolder
        ? (node.children || []).some((child) => walk(child, `${parentPath}/${child.name}`) !== null)
        : false;

      if (!matches && isFolder && !childMatches) {
        return null;
      }

      return { ...node, matches, childMatches, parentPath };
    };

    const rootNode = walk(tree);
    return rootNode;
  }, [tree, searchQuery, extensionFilter]);

  if (!visibleTree) {
    return <p className="empty-tree">No files match the current search or filter.</p>;
  }

  const toggleFolder = (name) => {
    setExpandedFolders((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const renderNode = (node, depth = 0, path = 'repository') => {
    const isFolder = node.type === 'folder';
    const isExpanded = expandedFolders[path] ?? true;

    if (isFolder && !isExpanded) {
      return (
        <div key={path} className="tree-node folder-compact" style={{ marginLeft: depth * 14 }}>
          <button type="button" className="tree-folder-toggle" onClick={() => toggleFolder(path)}>
            <ChevronRight size={14} />
            <FolderClosed size={14} />
            <span>{node.name}</span>
          </button>
        </div>
      );
    }

    return (
      <div key={path}>
        <div className="tree-node" style={{ marginLeft: depth * 14 }}>
          {isFolder ? (
            <button type="button" className="tree-folder-toggle" onClick={() => toggleFolder(path)}>
              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {isExpanded ? <FolderOpen size={14} /> : <FolderClosed size={14} />}
              <span>{node.name}</span>
            </button>
          ) : (
            <div className="tree-file-row">
              <span className="file-name"><FileText size={14} /> {node.name}</span>
              <span className="file-meta">{node.fileType || 'file'}</span>
              <span className="file-meta">{formatFileSize(node.size || 0)}</span>
            </div>
          )}
        </div>

        {isFolder && isExpanded && Array.isArray(node.children) ? (
          <div>
            {node.children
              .filter((child) => {
                if (!searchQuery) return true;
                const query = searchQuery.toLowerCase();
                if (child.type === 'folder') {
                  return child.name.toLowerCase().includes(query) || (child.children || []).some((grandchild) =>
                    grandchild.name.toLowerCase().includes(query)
                  );
                }
                return child.name.toLowerCase().includes(query);
              })
              .map((child) => renderNode(child, depth + 1, `${path}/${child.name}`))}
          </div>
        ) : null}
      </div>
    );
  };

  return <div className="repository-tree">{renderNode(visibleTree, 0, 'repository')}</div>;
}

export default RepositoryTree;
