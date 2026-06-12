import { Outlet } from 'react-router-dom';
import { ErrorBoundary } from './ErrorBoundary';
import { Sidebar } from './Sidebar';

export function Layout() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="layout__main">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
