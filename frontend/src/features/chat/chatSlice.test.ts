import { describe, expect, it } from 'vitest';
import type { Message } from '@/types';
import {
  addMessage,
  appendToken,
  chatReducer,
  clearMessages,
  finishStreaming,
  setMessageSources,
  setMessageToolCalls,
} from './chatSlice';

const streaming: Message = { id: 'a1', role: 'assistant', content: 'Hel', isStreaming: true };

function stateWith(...messages: Message[]) {
  return { messages };
}

describe('chatSlice', () => {
  it('adds a message', () => {
    const state = chatReducer(undefined, addMessage(streaming));
    expect(state.messages).toEqual([streaming]);
  });

  it('appends a streamed token to the matching message', () => {
    const state = chatReducer(stateWith(streaming), appendToken({ id: 'a1', token: 'lo' }));
    expect(state.messages[0].content).toBe('Hello');
  });

  it('sets sources and tool calls on the matching message', () => {
    let state = chatReducer(stateWith(streaming), setMessageSources({ id: 'a1', sources: ['s1'] }));
    state = chatReducer(
      state,
      setMessageToolCalls({ id: 'a1', toolCalls: [{ name: 'vector_search', args: { query: 'q' } }] }),
    );
    expect(state.messages[0].sources).toEqual(['s1']);
    expect(state.messages[0].toolCalls).toEqual([{ name: 'vector_search', args: { query: 'q' } }]);
  });

  it('marks a message as finished streaming', () => {
    const state = chatReducer(stateWith(streaming), finishStreaming('a1'));
    expect(state.messages[0].isStreaming).toBe(false);
  });

  it('ignores updates for an unknown id', () => {
    const before = stateWith(streaming);
    let state = chatReducer(before, appendToken({ id: 'nope', token: 'x' }));
    state = chatReducer(state, setMessageSources({ id: 'nope', sources: ['s'] }));
    state = chatReducer(state, setMessageToolCalls({ id: 'nope', toolCalls: [] }));
    state = chatReducer(state, finishStreaming('nope'));
    expect(state).toEqual(before);
  });

  it('clears all messages', () => {
    const state = chatReducer(stateWith(streaming), clearMessages());
    expect(state.messages).toEqual([]);
  });
});
