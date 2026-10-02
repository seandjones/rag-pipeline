import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { SourceCitations } from './SourceCitations';

describe('SourceCitations', () => {
  it('renders nothing when there are no sources', () => {
    const { container } = render(<SourceCitations sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('uses singular and plural labels', () => {
    const { rerender } = render(<SourceCitations sources={['Source: a.md\ntext']} />);
    expect(screen.getByRole('button', { name: /^1 source ▼$/ })).toBeInTheDocument();

    rerender(<SourceCitations sources={['Source: a.md\ntext', 'Source: b.md\ntext']} />);
    expect(screen.getByRole('button', { name: /^2 sources ▼$/ })).toBeInTheDocument();
  });

  it('expands to show each source header and excerpt', async () => {
    render(<SourceCitations sources={['Source: a.md\nfirst excerpt']} />);
    const toggle = screen.getByRole('button');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Source: a.md')).toBeInTheDocument();
    expect(screen.getByText('first excerpt')).toBeInTheDocument();
  });

  it('cuts excerpts at 200 characters with an ellipsis', async () => {
    render(<SourceCitations sources={[`Source: a.md\n${'x'.repeat(250)}`]} />);

    await userEvent.click(screen.getByRole('button'));

    expect(screen.getByText(`${'x'.repeat(200)}…`)).toBeInTheDocument();
  });
});
