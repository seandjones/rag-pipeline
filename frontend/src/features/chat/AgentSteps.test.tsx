import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AgentSteps } from './AgentSteps';

describe('AgentSteps', () => {
  it('lists each tool call with its query', () => {
    render(<AgentSteps toolCalls={[{ name: 'vector_search', args: { query: 'mfa policy' } }]} />);

    expect(screen.getByText('vector_search')).toBeInTheDocument();
    expect(screen.getByText('“mfa policy”')).toBeInTheDocument();
  });

  // Known defect D6: String(undefined) is "undefined", so a call with no query shows “undefined”.
  it.fails('shows no query text for a tool call without a query', () => {
    render(<AgentSteps toolCalls={[{ name: 'list_documents', args: {} }]} />);

    expect(screen.getByText('list_documents')).toBeInTheDocument();
    expect(screen.queryByText(/undefined/)).not.toBeInTheDocument();
  });
});
