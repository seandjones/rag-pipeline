import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from './api/baseApi';
import { chatReducer } from '@/features/chat/chatSlice';
import { ingestReducer } from '@/features/ingest/ingestSlice';

export const store = configureStore({
  reducer: {
    [baseApi.reducerPath]: baseApi.reducer,
    chat: chatReducer,
    ingest: ingestReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(baseApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
