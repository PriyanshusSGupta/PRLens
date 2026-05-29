import { useAuth } from '../hooks/useAuth';
import { ReactNode } from 'react';

export default function AuthRequired({ children }: { children: ReactNode }) {
  const { user, loading, login, warnings } = useAuth();

  if (loading) {
    return (
      <div className="rounded-card p-8 text-center max-w-md mx-auto mt-16"
        style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="rounded-card p-10 text-center max-w-md mx-auto mt-16"
        style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
        <h2 className="font-display text-xl font-semibold mb-2" style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
          Connect GitHub
        </h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-ink-2)' }}>
          Sign in with GitHub to start reviewing pull requests with PRLens.
        </p>
        <button
          onClick={login}
          className="rounded-pill px-6 py-2.5 text-sm font-medium transition-colors"
          style={{
            backgroundColor: 'var(--color-accent)',
            color: 'var(--color-paper)',
            border: 'none',
            transitionDuration: 'var(--dur-short)',
            transitionTimingFunction: 'var(--ease-out)',
          }}
        >
          Connect GitHub Account
        </button>
      </div>
    );
  }

  return (
    <>
      {warnings.length > 0 && (
        <div className="rounded-card p-3 mb-6 text-sm"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-severity-medium)' }}>
          <p className="font-medium mb-1" style={{ color: 'var(--color-severity-medium)' }}>⚠ Limited permissions</p>
          {warnings.map((w, i) => (
            <p key={i} className="text-xs" style={{ color: 'var(--color-ink-2)' }}>{w}</p>
          ))}
        </div>
      )}
      {children}
    </>
  );
}
