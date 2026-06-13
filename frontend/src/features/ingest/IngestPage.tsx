import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/app/hooks';
import { setActiveJob } from './ingestSlice';
import { IngestForm } from './IngestForm';
import { IngestProgress } from './IngestProgress';

export function IngestPage() {
  const dispatch = useAppDispatch();
  const activeJobId = useAppSelector((s) => s.ingest.activeJobId);

  const handleComplete = useCallback(() => {
    // keep showing result; user can start another job manually
  }, []);

  return (
    <div className="ingest-page">
      <h1>Ingest Documents</h1>
      <p className="ingest-page__description">
        Point the pipeline at a local directory. Supported formats: .txt, .md, .pdf.
      </p>

      <IngestForm />

      {activeJobId && (
        <div className="ingest-page__progress">
          <h2>Job {activeJobId.slice(0, 8)}…</h2>
          <IngestProgress jobId={activeJobId} onComplete={handleComplete} />
          <button
            className="ingest-page__new"
            onClick={() => dispatch(setActiveJob(null))}
          >
            Start new job
          </button>
        </div>
      )}
    </div>
  );
}
