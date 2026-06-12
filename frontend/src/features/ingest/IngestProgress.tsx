import { useEffect } from 'react';
import { useGetJobStatusQuery } from '@/app/api/ingestApi';

interface IngestProgressProps {
  jobId: string;
  onComplete?: () => void;
}

export function IngestProgress({ jobId, onComplete }: IngestProgressProps) {
  const { data, isLoading } = useGetJobStatusQuery(jobId, {
    pollingInterval: 2000,
    skip: !jobId,
  });

  useEffect(() => {
    if (data?.status === 'complete' || data?.status === 'failed') {
      onComplete?.();
    }
  }, [data?.status, onComplete]);

  if (isLoading || !data) return <p className="ingest-progress">Checking status…</p>;

  return (
    <div className="ingest-progress">
      <p className="ingest-progress__status">
        Status: <strong>{data.status}</strong>
      </p>
      {data.status === 'complete' && (
        <p className="ingest-progress__summary">
          {data.files_indexed} file{data.files_indexed !== 1 ? 's' : ''} indexed &mdash;{' '}
          {data.chunks_stored} chunks stored
        </p>
      )}
      {data.status === 'failed' && (
        <p className="ingest-progress__error">{data.error}</p>
      )}
    </div>
  );
}
