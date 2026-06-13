import { useDeleteDocumentMutation } from '@/app/api/documentsApi';

interface DocumentCardProps {
  sourcePath: string;
}

export function DocumentCard({ sourcePath }: DocumentCardProps) {
  const [deleteDocument, { isLoading }] = useDeleteDocumentMutation();
  const filename = sourcePath.split('/').pop() ?? sourcePath;

  return (
    <li className="doc-card">
      <div className="doc-card__info">
        <p className="doc-card__name" title={sourcePath}>{filename}</p>
        <p className="doc-card__path">{sourcePath}</p>
      </div>
      <button
        className="doc-card__delete"
        onClick={() => deleteDocument(sourcePath)}
        disabled={isLoading}
        aria-label={`Delete ${filename}`}
      >
        {isLoading ? '…' : 'Delete'}
      </button>
    </li>
  );
}
