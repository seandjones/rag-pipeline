import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Message, ToolCall } from '@/types';

interface ChatState {
  messages: Message[];
}

const initialState: ChatState = { messages: [] };

export const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage(state, action: PayloadAction<Message>) {
      state.messages.push(action.payload);
    },
    appendToken(state, action: PayloadAction<{ id: string; token: string }>) {
      const msg = state.messages.find((m) => m.id === action.payload.id);
      if (msg) msg.content += action.payload.token;
    },
    setMessageSources(state, action: PayloadAction<{ id: string; sources: string[] }>) {
      const msg = state.messages.find((m) => m.id === action.payload.id);
      if (msg) msg.sources = action.payload.sources;
    },
    setMessageToolCalls(state, action: PayloadAction<{ id: string; toolCalls: ToolCall[] }>) {
      const msg = state.messages.find((m) => m.id === action.payload.id);
      if (msg) msg.toolCalls = action.payload.toolCalls;
    },
    finishStreaming(state, action: PayloadAction<string>) {
      const msg = state.messages.find((m) => m.id === action.payload);
      if (msg) msg.isStreaming = false;
    },
    clearMessages(state) {
      state.messages = [];
    },
  },
});

export const {
  addMessage,
  appendToken,
  setMessageSources,
  setMessageToolCalls,
  finishStreaming,
  clearMessages,
} = chatSlice.actions;

export const chatReducer = chatSlice.reducer;
