import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const API = 'http://localhost/api';

export const handlers = [
  http.post(`${API}/chat`, () =>
    HttpResponse.json({
      answer: 'Access reviews happen quarterly.',
      sources: ['Source: access-control-policy.md\nUser access is reviewed quarterly.'],
      tool_calls: [{ name: 'vector_search', args: { query: 'access review frequency' } }],
    }),
  ),
];

export const server = setupServer(...handlers);
