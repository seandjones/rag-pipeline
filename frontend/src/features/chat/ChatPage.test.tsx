import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { API, server } from '@/test/server';
import { renderWithStore } from '@/test/renderWithStore';
import { ChatPage } from './ChatPage';

async function ask(question: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole('textbox'), `${question}{Enter}`);
}

describe('ChatPage', () => {
  it('shows the error message when the API fails', async () => {
    server.use(http.post(`${API}/chat`, () => new HttpResponse(null, { status: 500 })));
    renderWithStore(<ChatPage />);
    await ask('How often are access reviews?');
    expect(await screen.findByText('An error occurred. Please try again.')).toBeInTheDocument();
  });

  // Known defect D3: the placeholder assistant message is never replaced.
  it.fails('shows the answer exactly once, with its sources and agent steps', async () => {
    const { store } = renderWithStore(<ChatPage />);
    await ask('How often are access reviews?');
    expect(await screen.findByText('Access reviews happen quarterly.')).toBeInTheDocument();
    const assistant = store.getState().chat.messages.filter((m) => m.role === 'assistant');
    expect(assistant).toHaveLength(1);
    expect(screen.getByRole('button', { name: /1 source/ })).toBeInTheDocument();
    expect(screen.getByText('vector_search')).toBeInTheDocument();
  });

  // Known defect D4: history is captured from the first render and is always empty.
  it.fails('sends the previous turn as history on the next question', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/chat`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ answer: `answer ${bodies.length}`, sources: [], tool_calls: [] });
      }),
    );
    renderWithStore(<ChatPage />);
    await ask('first question');
    await screen.findByText('answer 1');
    await ask('second question');
    await screen.findByText('answer 2');
    expect(bodies[1]).toMatchObject({
      question: 'second question',
      messages: [
        { role: 'user', content: 'first question' },
        { role: 'assistant', content: 'answer 1' },
      ],
    });
  });

  it('answers a second question', async () => {
    let count = 0;
    server.use(
      http.post(`${API}/chat`, async () => {
        count += 1;
        return HttpResponse.json({ answer: `answer ${count}`, sources: [], tool_calls: [] });
      }),
    );
    renderWithStore(<ChatPage />);
    await ask('first question');
    await screen.findByText('answer 1');
    await ask('second question');
    expect(await screen.findByText('answer 2')).toBeInTheDocument();
  });

  it('clears the conversation', async () => {
    renderWithStore(<ChatPage />);
    await ask('How often are access reviews?');
    await screen.findByText('Access reviews happen quarterly.');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Clear' }));
    await waitFor(() =>
      expect(screen.getByText('Ask anything about your indexed documents.')).toBeInTheDocument(),
    );
  });
});
