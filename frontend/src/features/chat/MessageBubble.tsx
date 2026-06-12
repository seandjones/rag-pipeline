import type { Message } from '@/types';
import { AgentSteps } from './AgentSteps';
import { SourceCitations } from './SourceCitations';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`bubble bubble--${message.role}`}>
      <div className="bubble__content">
        <p className="bubble__text">
          {message.content}
          {message.isStreaming && <span className="bubble__cursor" aria-hidden>▌</span>}
        </p>
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <AgentSteps toolCalls={message.toolCalls} />
        )}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCitations sources={message.sources} />
        )}
      </div>
    </div>
  );
}
