import { Link } from 'react-router-dom';
import { usePRs } from '../hooks/usePrs';

export default function PRList() {
  const { prs, loading } = usePRs();

  const riskColor = (score: number) =>
    score > 0.6 ? 'var(--color-severity-critical)' : score > 0.3 ? 'var(--color-severity-high)' : 'var(--color-cat-testing)';

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-display text-3xl font-semibold mb-1.5" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
          Pull Requests
        </h1>
        <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>
          Recent review runs sorted by risk score
        </p>
      </div>

      {loading ? (
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading…</p>
      ) : prs.length === 0 ? (
        <div className="rounded-card p-8 text-center"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <p className="text-sm mb-1" style={{ color: 'var(--color-ink-2)' }}>No pull requests reviewed yet.</p>
          <p className="text-xs" style={{ color: 'var(--color-muted)' }}>
            PRLens will show pull requests here after they are submitted via webhook or manual review.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {prs.map((pr) => (
            <Link
              key={pr.id}
              to={`/prs/${pr.id}`}
              className="block rounded-card p-4 transition-colors"
              style={{
                backgroundColor: 'var(--color-paper-2)',
                border: '1px solid var(--color-rule-subtle)',
                transitionDuration: 'var(--dur-short)',
                transitionTimingFunction: 'var(--ease-out)',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-rule)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-rule-subtle)'; }}
            >
              <div className="flex items-center gap-3">
                <span className="font-outlier text-xs tabular-nums" style={{ color: 'var(--color-accent-dim)' }}>
                  #{pr.pr_number}
                </span>
                <span className="text-sm font-medium flex-1 truncate" style={{ color: 'var(--color-ink)' }}>
                  {pr.title}
                </span>
                <span className="text-xs" style={{ color: 'var(--color-ink-2)' }}>{pr.author}</span>
                {pr.risk_score != null && (
                  <span className="text-xs font-outlier font-medium"
                    style={{ color: riskColor(pr.risk_score) }}>
                    {(pr.risk_score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
