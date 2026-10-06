import { useRef, useState } from 'react';
import { FileArchive, FolderPlus, UploadCloud } from 'lucide-react';

function FileUpload({ onFilesSelected, label = 'Upload your project' }) {
  const inputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length) {
      onFilesSelected(selectedFiles);
    }
  };

  const openFileDialog = () => inputRef.current?.click();
  const openFolderDialog = () => folderInputRef.current?.click();

  return (
    <div
      className={`upload-zone ${isDragging ? 'dragging' : ''}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        const files = Array.from(event.dataTransfer.files || []);
        if (files.length) onFilesSelected(files);
      }}
    >
      <input ref={inputRef} type="file" multiple hidden onChange={handleFiles} />
      <input
        ref={folderInputRef}
        type="file"
        webkitdirectory=""
        directory=""
        multiple
        hidden
        onChange={handleFiles}
      />

      <UploadCloud size={36} />
      <h3>{label}</h3>
      <p>Drag and drop files or a complete folder here</p>

      <div className="upload-actions">
        <button type="button" className="primary-button" onClick={openFileDialog}>
          <FileArchive size={15} /> Browse Files
        </button>
        <button type="button" className="secondary-button" onClick={openFolderDialog}>
          <FolderPlus size={15} /> Select Folder
        </button>
      </div>
    </div>
  );
}

export default FileUpload;
