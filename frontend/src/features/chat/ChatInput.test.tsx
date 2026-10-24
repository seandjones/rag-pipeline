import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  it('submits the trimmed question on Enter and clears the box', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} />);
    const box = screen.getByRole('textbox');

    await userEvent.type(box, '  what is MFA?  {Enter}');

    expect(onSubmit).toHaveBeenCalledWith('what is MFA?');
    expect(box).toHaveValue('');
  });

  it('adds a newline on Shift+Enter instead of submitting', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} />);

    await userEvent.type(screen.getByRole('textbox'), 'line one{Shift>}{Enter}{/Shift}line two');

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox')).toHaveValue('line one\nline two');
  });

  it('ignores an empty question', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    await userEvent.type(screen.getByRole('textbox'), '   {Enter}');

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows "Thinking…" and blocks input while disabled', () => {
    render(<ChatInput onSubmit={vi.fn()} disabled />);

    expect(screen.getByRole('button', { name: 'Thinking…' })).toBeDisabled();
    expect(screen.getByRole('textbox')).toBeDisabled();
  });
});
