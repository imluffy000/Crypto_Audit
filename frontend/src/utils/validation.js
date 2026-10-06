export const DEFAULT_ALLOWED_EXTENSIONS = [
  '.py',
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  '.java',
  '.go',
  '.rs',
  '.cpp',
  '.c',
  '.h',
  '.json',
  '.yaml',
  '.yml',
  '.toml',
  '.md',
  '.txt',
  '.ini',
  '.env',
];

export const MAX_FILE_SIZE = 5 * 1024 * 1024;
export const MAX_REPOSITORY_SIZE = 250 * 1024 * 1024;

function normalizePath(path = '') {
  return path.replace(/\\/g, '/').replace(/^\//, '').trim();
}

export function validateRepositoryFiles(fileEntries = [], options = {}) {
  const allowedExtensions = options.allowedExtensions || DEFAULT_ALLOWED_EXTENSIONS;
  const maxFileSize = options.maxFileSize || MAX_FILE_SIZE;
  const maxRepositorySize = options.maxRepositorySize || MAX_REPOSITORY_SIZE;

  const validEntries = [];
  const invalidEntries = [];
  const duplicatePaths = [];
  const seenPaths = new Set();
  let totalSize = 0;

  fileEntries.forEach((entry) => {
    const normalizedPath = normalizePath(entry.relativePath || entry.path || entry.fileName || '');
    const isDuplicate = seenPaths.has(normalizedPath);
    if (isDuplicate) {
      duplicatePaths.push(normalizedPath);
      invalidEntries.push({ ...entry, reason: 'Duplicate file path detected' });
      return;
    }

    seenPaths.add(normalizedPath);

    const extension = (entry.fileType || '').toLowerCase();
    const isEmpty = (entry.fileSize || 0) === 0;
    const isTooLarge = (entry.fileSize || 0) > maxFileSize;
    const isUnsupportedExtension = !allowedExtensions.includes(extension) && extension !== '';
    const isInvalidPath = !normalizedPath || normalizedPath.includes('..') || normalizedPath.startsWith('/');

    totalSize += entry.fileSize || 0;

    if (isEmpty || isTooLarge || isUnsupportedExtension || isInvalidPath) {
      invalidEntries.push({
        ...entry,
        reason: isEmpty
          ? 'Empty file'
          : isTooLarge
            ? 'File exceeds recommended upload size'
            : isUnsupportedExtension
              ? 'Unsupported file type'
              : 'Invalid file path',
      });
      return;
    }

    validEntries.push(entry);
  });

  const repoTooLarge = totalSize > maxRepositorySize;

  return {
    totalFiles: fileEntries.length,
    totalSize,
    validFiles: validEntries.length,
    invalidFiles: invalidEntries.length,
    validEntries,
    invalidEntries,
    duplicatePaths,
    repoTooLarge,
    maxFileSize,
    maxRepositorySize,
  };
}
