import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from './api/baseApi';
import { chatReducer } from '@/features/chat/chatSlice';
import { ingestReducer } from '@/features/ingest/ingestSlice';

// A factory so tests can start each case from a clean store; the app uses the singleton below.
export function makeStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      chat: chatReducer,
      ingest: ingestReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(baseApi.middleware),
  });
}

export const store = makeStore();

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore['getState']>;
export type AppDispatch = AppStore['dispatch'];
