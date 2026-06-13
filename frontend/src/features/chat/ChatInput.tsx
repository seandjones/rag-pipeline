import { useRef, type KeyboardEvent } from 'react';

interface ChatInputProps {
  onSubmit: (question: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSubmit, disabled = false }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const value = ref.current?.value.trim();
    if (!value || disabled) return;
    onSubmit(value);
    if (ref.current) ref.current.value = '';
  }

  return (
    <div className="chat-input">
      <textarea
        ref={ref}
        className="chat-input__textarea"
        placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={3}
      />
      <button
        className="chat-input__submit"
        onClick={submit}
        disabled={disabled}
      >
        {disabled ? 'Thinking…' : 'Send'}
      </button>
    </div>
  );
}
