import type { ReactElement } from 'react';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { makeStore } from '@/app/store';

export function renderWithStore(ui: ReactElement) {
  const store = makeStore();
  return { store, ...render(<Provider store={store}>{ui}</Provider>) };
}
