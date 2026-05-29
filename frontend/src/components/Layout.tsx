import { Link, useLocation, Outlet, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '../hooks/useAuth';

function NavBar() {
  const location = useLocation();
  const { user, logout } = useAuth();

  if (!user) return null;

  const navLinks = [
    { to: '/', label: 'Dashboard' },
    { to: '/prs', label: 'PRs' },
    { to: '/repos', label: 'Repos' },
    { to: '/evaluations', label: 'Evals' },
  ];

  return (
    <header className="sticky top-0 z-10 backdrop-blur-md"
      style={{
        backgroundColor: 'color-mix(in oklch, var(--color-paper) 88%, transparent)',
        borderBottom: '1px solid var(--color-rule-subtle)',
      }}>
      <div className="max-w-6xl mx-auto flex items-center justify-between h-14 px-6">
        <Link
          to="/"
          className="font-display text-base font-semibold tracking-tight"
          style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}
        >
          PRLens
        </Link>
        <nav className="flex items-center gap-1">
          {navLinks.map((link) => {
            const active = location.pathname === link.to || (link.to !== '/' && location.pathname.startsWith(link.to));
            return (
              <Link
                key={link.to}
                to={link.to}
                className="px-3 py-1.5 text-sm rounded-pill transition-colors"
                style={{
                  color: active ? 'var(--color-ink)' : 'var(--color-ink-2)',
                  backgroundColor: active ? 'var(--color-paper-3)' : 'transparent',
                  fontWeight: active ? 500 : 400,
                  transitionDuration: 'var(--dur-short)',
                  transitionTimingFunction: 'var(--ease-out)',
                }}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            to="/ai"
            className="text-sm rounded-pill px-3 py-1.5 transition-colors"
            style={{ color: 'var(--color-ink-2)', transitionDuration: 'var(--dur-short)' }}
          >
            ⚙ AI
          </Link>
          <span className="text-xs" style={{ color: 'var(--color-ink-2)' }}>{user.username || user.email}</span>
          <button
            onClick={logout}
            className="text-xs rounded-pill px-3 py-1 transition-colors"
            style={{ color: 'var(--color-ink-2)', border: '1px solid var(--color-rule-subtle)', transitionDuration: 'var(--dur-short)' }}
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}

function ProtectedLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-paper)' }}>
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading…</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--color-paper)' }}>
      <NavBar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}

export default function Layout() {
  return (
    <AuthProvider>
      <ProtectedLayout />
    </AuthProvider>
  );
}
