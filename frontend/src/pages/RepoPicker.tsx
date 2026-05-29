import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../lib/api';

interface Repo {
  id: number;
  full_name: string;
  description: string | null;
  private: boolean;
  updated_at: string;
  installed: boolean;
  webhook_status: string | null;
}

export default function RepoPicker() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [toggleLoading, setToggleLoading] = useState<string | null>(null);
  const [needsGithubConnect, setNeedsGithubConnect] = useState(false);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (searchParams.get('connect_github') === 'true') {
      setNeedsGithubConnect(true);
    }
  }, [searchParams]);

  useEffect(() => {
    setLoading(true);
    api.get(`/repos?page=${page}`)
      .then(r => { setRepos(r.data); setNeedsGithubConnect(false); })
      .catch(err => {
        if (err.response?.status === 401) {
          setNeedsGithubConnect(true);
        }
      })
      .finally(() => setLoading(false));
  }, [page]);

  const handleConnectGithub = async () => {
    setLoading(true);
    try {
      const res = await api.get('/auth/github-connect/login');
      window.location.href = res.data.redirect_url;
    } catch {
      setLoading(false);
    }
  };

  const handleToggle = async (repo: Repo) => {
    setToggleLoading(repo.full_name);
    try {
      if (repo.installed) {
        await api.post('/repos/uninstall', { full_name: repo.full_name });
        setRepos(prev => prev.map(r => r.full_name === repo.full_name ? { ...r, installed: false, webhook_status: null } : r));
      } else {
        await api.post('/repos/install', { full_name: repo.full_name });
        setRepos(prev => prev.map(r => r.full_name === repo.full_name ? { ...r, installed: true, webhook_status: 'active' } : r));
      }
    } catch {
      alert('Operation failed');
    }
    setToggleLoading(null);
  };

  const filtered = repos.filter(r =>
    r.full_name.toLowerCase().includes(search.toLowerCase())
  );

  if (needsGithubConnect) {
    return (
      <div>
        <h1 className="font-display text-2xl font-semibold mb-1.5" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
          Repositories
        </h1>
        <p className="text-sm mb-6" style={{ color: 'var(--color-ink-2)' }}>
          Connect GitHub to access your repositories
        </p>
        <div className="rounded-card p-8 text-center"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <p className="text-sm mb-4" style={{ color: 'var(--color-ink-2)' }}>
            PRLens needs access to your GitHub repositories to install webhooks and run reviews.
          </p>
          <button
            onClick={handleConnectGithub}
            disabled={loading}
            className="rounded-pill px-6 py-2.5 text-sm font-medium transition-colors"
            style={{
              backgroundColor: loading ? 'var(--color-paper-3)' : '#24292e',
              color: '#fff',
              border: 'none',
              transitionDuration: 'var(--dur-short)',
              transitionTimingFunction: 'var(--ease-out)',
            }}
          >
            <span className="flex items-center justify-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
              {loading ? 'Connecting…' : 'Connect GitHub Repositories'}
            </span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-semibold mb-1.5" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
        Repositories
      </h1>
      <p className="text-sm mb-6" style={{ color: 'var(--color-ink-2)' }}>
        Install PRLens webhooks on your repositories to enable automatic reviews.
      </p>

      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search repositories…"
        className="w-full rounded-input px-3 py-2 text-sm mb-4"
        style={{
          backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)',
        }}
      />

      {loading ? (
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading repositories…</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {filtered.map(repo => (
            <div
              key={repo.id}
              className="rounded-card p-4"
              style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}
            >
              <div className="flex items-start gap-3 mb-2">
                <span className="text-sm font-medium flex-1 truncate" style={{ color: 'var(--color-ink)' }}>
                  {repo.full_name}
                </span>
                {repo.private && (
                  <span className="text-xs px-1.5 py-0.5 rounded-pill" style={{ backgroundColor: 'var(--color-paper-3)', color: 'var(--color-ink-2)' }}>
                    private
                  </span>
                )}
                {repo.installed && (
                  <span className="text-xs px-1.5 py-0.5 rounded-pill" style={{ backgroundColor: 'var(--color-cat-testing)', color: '#fff' }}>
                    installed
                  </span>
                )}
              </div>
              {repo.description && (
                <p className="text-xs mb-3 line-clamp-2" style={{ color: 'var(--color-ink-2)' }}>{repo.description}</p>
              )}
              <button
                onClick={() => handleToggle(repo)}
                disabled={toggleLoading === repo.full_name}
                className="text-xs rounded-pill px-4 py-1.5 font-medium transition-colors disabled:opacity-50"
                style={{
                  color: repo.installed ? 'var(--color-severity-critical)' : 'var(--color-accent)',
                  border: `1px solid ${repo.installed ? 'var(--color-severity-critical)' : 'var(--color-accent)'}`,
                  backgroundColor: 'transparent',
                  transitionDuration: 'var(--dur-short)',
                }}
              >
                {toggleLoading === repo.full_name ? 'Working…' : repo.installed ? 'Uninstall' : 'Install'}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3 justify-center mt-6">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="text-sm rounded-pill px-4 py-1.5 transition-colors disabled:opacity-30"
          style={{ color: 'var(--color-ink-2)', border: '1px solid var(--color-rule-subtle)', transitionDuration: 'var(--dur-short)' }}
        >
          Previous
        </button>
        <button
          onClick={() => setPage(p => p + 1)}
          className="text-sm rounded-pill px-4 py-1.5 transition-colors"
          style={{ color: 'var(--color-ink-2)', border: '1px solid var(--color-rule-subtle)', transitionDuration: 'var(--dur-short)' }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
