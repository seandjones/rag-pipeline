import type { ChatResponse } from '@/types';
import { baseApi } from './baseApi';

interface ChatRequest {
  question: string;
  top_k?: number;
}

export const chatApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    chat: builder.mutation<ChatResponse, ChatRequest>({
      query: (body) => ({
        url: '/chat',
        method: 'POST',
        body,
      }),
    }),
  }),
});

export const { useChatMutation } = chatApi;
