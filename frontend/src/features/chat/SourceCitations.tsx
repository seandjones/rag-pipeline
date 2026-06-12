import { useState } from 'react';

interface SourceCitationsProps {
  sources: string[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [open, setOpen] = useState(false);
  if (sources.length === 0) return null;

  return (
    <div className="citations">
      <button
        className="citations__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {sources.length} source{sources.length !== 1 ? 's' : ''} {open ? '▲' : '▼'}
      </button>
      {open && (
        <ul className="citations__list">
          {sources.map((src, i) => {
            const lines = src.split('\n');
            const header = lines[0] ?? '';
            const body = lines.slice(1).join('\n').trim();
            return (
              <li key={i} className="citations__item">
                <p className="citations__source">{header}</p>
                {body && <p className="citations__excerpt">{body.slice(0, 200)}{body.length > 200 ? '…' : ''}</p>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
