import { useRef, useState } from 'react';
import { FilePlus2, FolderPlus, Upload } from 'lucide-react';
import Button from './ui/Button';

function FileUpload({ onFilesSelected, label = 'Drop files or a folder here' }) {
  const inputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length) {
      onFilesSelected(selectedFiles);
    }
  };

  return (
    <div
      className={`dropzone ${isDragging ? 'is-dragging' : ''}`}
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
      <input ref={folderInputRef} type="file" webkitdirectory="" directory="" multiple hidden onChange={handleFiles} />

      <Upload size={22} aria-hidden="true" className="dropzone-icon" />
      <p className="dropzone-title">{label}</p>
      <p className="dropzone-hint">Files are read in your browser only. Nothing is uploaded to the server.</p>

      <div className="dropzone-actions">
        <Button icon={FilePlus2} onClick={() => inputRef.current?.click()}>
          Choose files
        </Button>
        <Button icon={FolderPlus} onClick={() => folderInputRef.current?.click()}>
          Choose folder
        </Button>
      </div>
    </div>
  );
}

export default FileUpload;
