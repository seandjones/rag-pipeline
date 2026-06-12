import type { ToolCall } from '@/types';

interface AgentStepsProps {
  toolCalls: ToolCall[];
}

export function AgentSteps({ toolCalls }: AgentStepsProps) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="agent-steps">
      <p className="agent-steps__label">Agent steps</p>
      <ul className="agent-steps__list">
        {toolCalls.map((tc, i) => (
          <li key={i} className="agent-steps__item">
            <span className="agent-steps__tool">{String(tc.name)}</span>
            {String(tc.args.query as string) && (
              <span className="agent-steps__arg">&ldquo;{String(tc.args.query as string)}&rdquo;</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
