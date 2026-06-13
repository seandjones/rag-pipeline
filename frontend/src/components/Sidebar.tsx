import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Chat', end: true },
  { to: '/ingest', label: 'Ingest', end: false },
  { to: '/documents', label: 'Documents', end: false },
] as const;

export function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="sidebar__brand">RAG Pipeline</div>
      <ul className="sidebar__nav">
        {NAV_ITEMS.map(({ to, label, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                `sidebar__link${isActive ? ' sidebar__link--active' : ''}`
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
