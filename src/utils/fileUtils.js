export function formatFileSize(bytes = 0) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function getFileExtension(fileName = '') {
  if (!fileName) return '';
  const idx = fileName.lastIndexOf('.');
  return idx >= 0 ? fileName.slice(idx).toLowerCase() : '';
}

export function normalizeFileEntry(file, index) {
  const relativePath = file.webkitRelativePath || file.name;
  const fileName = relativePath.split('/').pop();

  return {
    id: `${relativePath}-${index}`,
    relativePath,
    fileName,
    fileSize: file.size,
    fileType: getFileExtension(fileName),
    name: fileName,
    lastModified: file.lastModified,
    kind: file.type || 'file',
    webkitRelativePath: file.webkitRelativePath,
    sizeLabel: formatFileSize(file.size),
  };
}

export function buildTreeFromFiles(fileEntries = []) {
  const root = { name: 'repository', type: 'folder', children: [] };

  fileEntries.forEach((entry) => {
    const segments = entry.relativePath.split('/').filter(Boolean);
    let current = root;

    segments.forEach((segment, index) => {
      const isFile = index === segments.length - 1;
      const existing = current.children.find((child) => child.name === segment);

      if (existing) {
        current = existing;
        return;
      }

      const node = {
        name: segment,
        type: isFile ? 'file' : 'folder',
        children: isFile ? [] : [],
        size: isFile ? entry.fileSize : 0,
        fileType: isFile ? getFileExtension(segment) : '',
      };

      current.children.push(node);
      current = node;
    });
  });

  return root;
}
