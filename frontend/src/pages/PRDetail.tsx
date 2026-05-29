import { useParams } from 'react-router-dom';
import { useFindings } from '../hooks/useFindings';
import FindingCard from '../components/FindingCard';
import { useState, useEffect } from 'react';
import api from '../lib/api';

interface PRData {
  id: number;
  pr_number: number;
  title: string;
  state: string;
  author: string;
  risk_score: number;
  url: string;
  findings_count: number;
  file_risk: Record<string, { risk: number; count: number }>;
}

const CATEGORIES = ['All', 'Security', 'Reliability', 'Performance', 'Maintainability', 'Testing'];

export default function PRDetail() {
  const { id } = useParams<{ id: string }>();
  const prId = parseInt(id || '0', 10);
  const { findings, loading } = useFindings(prId);
  const [pr, setPr] = useState<PRData | null>(null);
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    api.get(`/prs/${prId}`).then(r => setPr(r.data)).catch(() => {});
  }, [prId]);

  const filtered = filter === 'All' ? findings : findings.filter(f => f.category.toLowerCase() === filter.toLowerCase());

  const riskColor = (s: number) =>
    s > 0.6 ? 'var(--color-severity-critical)' : s > 0.3 ? 'var(--color-severity-high)' : 'var(--color-cat-testing)';

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-baseline gap-3 mb-1.5">
          <span className="font-outlier text-sm tabular-nums" style={{ color: 'var(--color-accent-dim)' }}>
            #{pr?.pr_number || id}
          </span>
          <h1 className="font-display text-2xl font-semibold" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
            {pr?.title || 'Pull Request'}
          </h1>
        </div>
        <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>
          by {pr?.author || '—'} · {pr?.findings_count || findings.length} findings
        </p>
      </div>

      {pr && (
        <div className="rounded-card p-5 mb-6"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <div className="flex items-center gap-4 mb-3">
            <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--color-muted)', fontWeight: 500 }}>Risk Score</span>
            <span className="font-display text-3xl font-semibold"
              style={{ color: riskColor(pr.risk_score), letterSpacing: '-0.02em' }}>
              {(pr.risk_score * 100).toFixed(0)}%
            </span>
          </div>
          {Object.keys(pr.file_risk).length > 0 && (
            <div>
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>Per-file risk</span>
              <div className="mt-2 space-y-1">
                {Object.entries(pr.file_risk).slice(0, 5).map(([file, info]) => (
                  <div key={file} className="flex items-center gap-2 text-xs">
                    <span className="font-outlier flex-1 truncate" style={{ color: 'var(--color-ink-2)' }}>{file}</span>
                    <span className="tabular-nums" style={{ color: riskColor(info.risk) }}>{(info.risk * 100).toFixed(0)}%</span>
                    <span style={{ color: 'var(--color-muted)' }}>{info.count} findings</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2 mb-6 flex-wrap">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className="text-xs rounded-pill px-3 py-1 font-medium transition-colors"
            style={{
              color: filter === cat ? 'var(--color-paper)' : 'var(--color-ink-2)',
              backgroundColor: filter === cat ? 'var(--color-accent)' : 'var(--color-paper-2)',
              border: `1px solid ${filter === cat ? 'var(--color-accent)' : 'var(--color-rule-subtle)'}`,
              transitionDuration: 'var(--dur-short)',
              transitionTimingFunction: 'var(--ease-out)',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading findings…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-card p-8 text-center"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <p className="text-sm mb-1" style={{ color: 'var(--color-ink-2)' }}>No findings matching filter.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(finding => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}
