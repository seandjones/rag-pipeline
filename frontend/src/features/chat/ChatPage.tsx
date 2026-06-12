import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppDispatch, useAppSelector } from '@/app/hooks';
import { useChatMutation } from '@/app/api/chatApi';
import {
  addMessage,
  clearMessages,
  setMessageSources,
  setMessageToolCalls,
} from './chatSlice';
import { ChatInput } from './ChatInput';
import { MessageList } from './MessageList';

export function ChatPage() {
  const dispatch = useAppDispatch();
  const messages = useAppSelector((s) => s.chat.messages);
  const [sendChat, { isLoading }] = useChatMutation();

  const handleSubmit = useCallback(
    async (question: string) => {
      const userMsgId = uuidv4();
      dispatch(addMessage({ id: userMsgId, role: 'user', content: question }));

      const assistantMsgId = uuidv4();
      dispatch(
        addMessage({ id: assistantMsgId, role: 'assistant', content: '', isStreaming: true }),
      );

      try {
        const result = await sendChat({ question, top_k: 5 }).unwrap();
        dispatch(
          addMessage({
            id: assistantMsgId,
            role: 'assistant',
            content: result.answer,
            sources: result.sources,
            toolCalls: result.tool_calls,
            isStreaming: false,
          }),
        );
        // Replace the placeholder we added above
        dispatch(
          setMessageSources({ id: assistantMsgId, sources: result.sources }),
        );
        dispatch(
          setMessageToolCalls({ id: assistantMsgId, toolCalls: result.tool_calls }),
        );
      } catch {
        dispatch(
          addMessage({
            id: assistantMsgId,
            role: 'assistant',
            content: 'An error occurred. Please try again.',
            isStreaming: false,
          }),
        );
      }
    },
    [dispatch, sendChat],
  );

  return (
    <div className="chat-page">
      <div className="chat-page__header">
        <h1>Chat</h1>
        {messages.length > 0 && (
          <button className="chat-page__clear" onClick={() => dispatch(clearMessages())}>
            Clear
          </button>
        )}
      </div>
      <MessageList messages={messages} />
      <ChatInput onSubmit={handleSubmit} disabled={isLoading} />
    </div>
  );
}
