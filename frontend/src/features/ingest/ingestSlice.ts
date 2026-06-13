import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

interface IngestState {
  activeJobId: string | null;
}

const initialState: IngestState = { activeJobId: null };

export const ingestSlice = createSlice({
  name: 'ingest',
  initialState,
  reducers: {
    setActiveJob(state, action: PayloadAction<string | null>) {
      state.activeJobId = action.payload;
    },
  },
});

export const { setActiveJob } = ingestSlice.actions;
export const ingestReducer = ingestSlice.reducer;
