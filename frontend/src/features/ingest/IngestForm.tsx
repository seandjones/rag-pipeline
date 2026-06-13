import { useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { useUploadFilesMutation } from '@/app/api/ingestApi';
import { useAppDispatch } from '@/app/hooks';
import { setActiveJob } from './ingestSlice';

const ACCEPTED_EXTENSIONS = new Set(['.txt', '.md', '.pdf', '.csv', '.json', '.rst']);

function filterFiles(fileList: FileList): File[] {
  return Array.from(fileList).filter((f) => {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    return ACCEPTED_EXTENSIONS.has(ext);
  });
}

export function IngestForm() {
  const dispatch = useAppDispatch();
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadFiles, { isLoading, error }] = useUploadFilesMutation();

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      setSelectedFiles(filterFiles(e.target.files));
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      const relativePath =
        (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
      formData.append('files', file, relativePath);
    });
    formData.append('chunk_size', '1000');
    formData.append('overlap', '100');

    try {
      const result = await uploadFiles(formData).unwrap();
      dispatch(setActiveJob(result.job_id));
      setSelectedFiles([]);
      if (inputRef.current) inputRef.current.value = '';
    } catch {
      // error shown via RTK Query error state
    }
  }

  const folderName = selectedFiles[0]
    ? ((selectedFiles[0] as File & { webkitRelativePath?: string }).webkitRelativePath?.split(
        '/',
      )[0] ?? 'selected folder')
    : null;

  return (
    <form className="ingest-form" onSubmit={handleSubmit}>
      {/* webkitdirectory is non-standard and not in TS types — spread as a plain object */}
      <input
        ref={inputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
        {...({ webkitdirectory: '' } as Record<string, string>)}
      />

      <button
        type="button"
        className="ingest-form__pick"
        onClick={() => inputRef.current?.click()}
      >
        Choose folder
      </button>

      {folderName && (
        <div className="ingest-form__selected">
          <span className="ingest-form__folder">{folderName}</span>
          <span className="ingest-form__count">
            {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
          </span>
        </div>
      )}

      <button
        className="ingest-form__submit"
        type="submit"
        disabled={isLoading || selectedFiles.length === 0}
      >
        {isLoading ? 'Uploading…' : 'Start ingestion'}
      </button>

      {error && (
        <p className="ingest-form__error">
          {'data' in error
            ? JSON.stringify((error as { data: unknown }).data)
            : 'Upload failed'}
        </p>
      )}
    </form>
  );
}
