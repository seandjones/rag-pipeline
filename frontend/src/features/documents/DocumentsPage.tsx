import { useListDocumentsQuery } from '@/app/api/documentsApi';
import { DocumentCard } from './DocumentCard';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export function DocumentsPage() {
  const { data, isLoading, isError, refetch } = useListDocumentsQuery();

  return (
    <div className="documents-page">
      <div className="documents-page__header">
        <h1>Indexed Documents</h1>
        <button className="documents-page__refresh" onClick={refetch}>
          Refresh
        </button>
      </div>

      {isLoading && <LoadingSpinner />}

      {isError && (
        <p className="documents-page__error">Failed to load documents.</p>
      )}

      {data && data.documents.length === 0 && (
        <p className="documents-page__empty">
          No documents indexed yet. Go to <strong>Ingest</strong> to add some.
        </p>
      )}

      {data && data.documents.length > 0 && (
        <>
          <p className="documents-page__count">{data.total} document{data.total !== 1 ? 's' : ''}</p>
          <ul className="documents-page__list">
            {data.documents.map((doc) => (
              <DocumentCard key={doc} sourcePath={doc} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
