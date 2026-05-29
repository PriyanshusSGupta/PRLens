import { useState, useEffect } from 'react';
import api from '../lib/api';
import { useAuth } from '../hooks/useAuth';

interface ReviewResult {
  pr_number: number;
  title: string;
  author: string;
  state: string;
  risk_score: number;
  findings: Array<{
    severity: string;
    category: string;
    file_path: string;
    message: string;
    suggestion: string | null;
    confidence: number;
  }>;
  files_changed: number;
  pr_id: number | null;
}

interface DashboardStats {
  total_prs: number;
  total_findings: number;
  avg_risk_score: number;
  findings_by_severity: Record<string, number>;
  findings_by_category: Record<string, number>;
  recent_prs: Array<{
    id: number;
    pr_number: number;
    title: string;
    author: string;
    risk_score: number;
  }>;
}

export default function Dashboard() {
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [prNumber, setPrNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    api.get('/dashboard/summary')
      .then(r => setStats(r.data))
      .catch(() => {});
  }, []);

  const handleReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setLoading(true);
    try {
      const res = await api.post('/review', {
        owner: owner.trim(),
        repo: repo.trim(),
        pr_number: parseInt(prNumber, 10),
      });
      setResult(res.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch review';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => setResult(null)}
            className="text-sm rounded-pill px-3 py-1 transition-colors"
            style={{
              color: 'var(--color-ink-2)', backgroundColor: 'var(--color-paper-2)',
              border: '1px solid var(--color-rule-subtle)',
              transitionDuration: 'var(--dur-short)', transitionTimingFunction: 'var(--ease-out)',
            }}
          >
            ← Back
          </button>
          <h1 className="font-display text-3xl font-semibold" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
            Review Complete
          </h1>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <StatCard label="Risk Score" value={result.risk_score === 0 ? 'Clean' : `${(result.risk_score * 100).toFixed(0)}%`} />
          <StatCard label="Findings" value={`${result.findings.length}`} />
          <StatCard label="Files Changed" value={`${result.files_changed}`} />
        </div>

        <div className="mb-6">
          <h2 className="font-display text-xl font-semibold mb-1" style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
            {result.title}
          </h2>
          <p style={{ color: 'var(--color-ink-2)' }}>PR #{result.pr_number} by {result.author}</p>
        </div>

        <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-ink-2)' }}>Findings</h3>
        <div className="space-y-3">
          {result.findings.map((f, i) => (
            <div key={i} className="rounded-card p-5"
              style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-block px-2.5 py-0.5 rounded-pill text-xs font-semibold"
                  style={{
                    backgroundColor: ({ critical: 'var(--color-severity-critical)', high: 'var(--color-severity-high)',
                      medium: 'var(--color-severity-medium)', low: 'var(--color-severity-low)' })[f.severity] || 'var(--color-muted)',
                    color: '#fff',
                  }}>
                  {f.severity.toUpperCase()}
                </span>
                <span className="text-xs font-medium" style={{
                  color: ({ security: 'var(--color-cat-security)', reliability: 'var(--color-cat-reliability)',
                    performance: 'var(--color-cat-performance)', maintainability: 'var(--color-cat-maintainability)',
                    testing: 'var(--color-cat-testing)' })[f.category] || 'var(--color-muted)',
                }}>{f.category}</span>
                <span className="text-xs ml-auto font-outlier tabular-nums" style={{ color: 'var(--color-muted)' }}>
                  {(f.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-sm mb-1.5" style={{ color: 'var(--color-ink)' }}>{f.message}</p>
              {f.file_path && (
                <p className="text-xs mb-3 font-outlier" style={{ color: 'var(--color-ink-2)' }}>{f.file_path}</p>
              )}
              {f.suggestion && (
                <div className="pt-3 mt-1 text-xs" style={{ borderTop: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink-2)' }}>
                  <span className="font-medium" style={{ color: 'var(--color-accent)' }}>Suggestion</span>
                  <span className="ml-1.5">{f.suggestion}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-display text-3xl font-semibold mb-1.5" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
          Dashboard
        </h1>
        <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>
          Review any GitHub pull request — connected as <strong>{user?.username}</strong>
        </p>
      </div>

      <form onSubmit={handleReview} className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_120px_auto] gap-3 items-end mb-8">
        <div>
          <label className="block text-xs mb-1.5" style={{ color: 'var(--color-muted)' }}>Owner</label>
          <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="facebook" required
            className="w-full rounded-input px-3 py-2 text-sm"
            style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)' }} />
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: 'var(--color-muted)' }}>Repo</label>
          <input type="text" value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="react" required
            className="w-full rounded-input px-3 py-2 text-sm"
            style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)' }} />
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: 'var(--color-muted)' }}>PR #</label>
          <input type="number" value={prNumber} onChange={(e) => setPrNumber(e.target.value)} placeholder="42" required min={1}
            className="w-full rounded-input px-3 py-2 text-sm"
            style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)' }} />
        </div>
        <button type="submit" disabled={loading}
          className="text-sm rounded-pill px-5 py-2 font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
          style={{
            color: loading ? 'var(--color-muted)' : 'var(--color-paper)',
            backgroundColor: loading ? 'var(--color-paper-3)' : 'var(--color-accent)',
            border: 'none', transitionDuration: 'var(--dur-short)', transitionTimingFunction: 'var(--ease-out)',
          }}>
          {loading ? 'Reviewing…' : 'Review'}
        </button>
      </form>

      {error && (
        <div className="rounded-card p-4 mb-6 text-sm"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-severity-high)', color: 'var(--color-severity-high)' }}>
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <StatCard label="PRs Reviewed" value={`${stats?.total_prs || 0}`} />
        <StatCard label="Findings" value={`${stats?.total_findings || 0}`} />
        <StatCard label="Avg Risk Score" value={stats?.avg_risk_score != null ? `${(stats.avg_risk_score * 100).toFixed(0)}%` : '—'} />
      </div>

      {stats?.recent_prs && stats.recent_prs.length > 0 && (
        <div className="rounded-card p-5 mb-8"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-ink-2)' }}>Recent Reviews</h3>
          <div className="space-y-2">
            {stats.recent_prs.map(pr => (
              <div key={pr.id} className="flex items-center gap-3 py-2"
                style={{ borderBottom: '1px solid var(--color-rule-subtle)' }}>
                <span className="text-xs font-outlier tabular-nums" style={{ color: 'var(--color-accent-dim)' }}>#{pr.pr_number}</span>
                <span className="text-sm flex-1" style={{ color: 'var(--color-ink)' }}>{pr.title}</span>
                <span className="text-xs" style={{ color: 'var(--color-ink-2)' }}>{pr.author}</span>
                <span className="text-xs font-outlier" style={{
                  color: pr.risk_score > 0.6 ? 'var(--color-severity-critical)' : pr.risk_score > 0.3 ? 'var(--color-severity-high)' : 'var(--color-cat-testing)',
                }}>
                  {(pr.risk_score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-card p-6"
        style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
        <p className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--color-muted)', fontWeight: 500 }}>What happens</p>
        <div className="space-y-2 text-sm" style={{ color: 'var(--color-ink-2)' }}>
          <div className="flex gap-2"><span className="font-outlier text-xs" style={{ color: 'var(--color-accent-dim)' }}>1</span>
            <span>PRLens fetches the pull request diff from GitHub's API</span></div>
          <div className="flex gap-2"><span className="font-outlier text-xs" style={{ color: 'var(--color-accent-dim)' }}>2</span>
            <span>Analyzers scan for security risks, reliability issues, performance patterns, and testing gaps</span></div>
          <div className="flex gap-2"><span className="font-outlier text-xs" style={{ color: 'var(--color-accent-dim)' }}>3</span>
            <span>Findings are scored and prioritized by severity and confidence</span></div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card p-5" style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
      <p className="text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--color-muted)', fontWeight: 500 }}>{label}</p>
      <p className="font-display text-3xl font-semibold tabular-nums" style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
        {value}
      </p>
    </div>
  );
}
