import { useState, useEffect } from 'react';
import api from '../lib/api';

interface EvalRun {
  id: number;
  pr_id: number;
  prompt_version: string;
  status: string;
  precision: number | null;
  false_positive_rate: number | null;
  coverage: number | null;
  created_at: string;
}

export default function Evaluation() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/evaluations').then(r => { setRuns(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-display text-3xl font-semibold mb-1.5" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
          Evaluations
        </h1>
        <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>
          Measure review quality against ground-truth annotations
        </p>
      </div>

      {loading ? (
        <p className="text-sm" style={{ color: 'var(--color-muted)' }}>Loading…</p>
      ) : runs.length === 0 ? (
        <div className="rounded-card p-8 text-center"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <p className="text-sm mb-1" style={{ color: 'var(--color-ink-2)' }}>No evaluation runs yet.</p>
          <p className="text-xs" style={{ color: 'var(--color-muted)' }}>
            Evaluation runs compare PRLens findings against ground-truth reviewer annotations
            to measure precision, false positive rate, and coverage.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-3 text-xs font-medium px-3"
            style={{ color: 'var(--color-muted)' }}>
            <span>Prompt</span><span>Precision</span><span>FPR</span><span>Coverage</span><span>Status</span>
          </div>
          {runs.map(run => (
            <div key={run.id} className="rounded-card p-4 grid grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-3 text-sm"
              style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
              <span className="font-outlier" style={{ color: 'var(--color-accent-dim)' }}>v{run.prompt_version}</span>
              <span className="tabular-nums" style={{ color: 'var(--color-cat-testing)' }}>
                {run.precision != null ? `${(run.precision * 100).toFixed(0)}%` : '—'}
              </span>
              <span className="tabular-nums" style={{ color: 'var(--color-severity-high)' }}>
                {run.false_positive_rate != null ? `${(run.false_positive_rate * 100).toFixed(0)}%` : '—'}
              </span>
              <span className="tabular-nums" style={{ color: 'var(--color-accent)' }}>
                {run.coverage != null ? `${(run.coverage * 100).toFixed(0)}%` : '—'}
              </span>
              <span style={{ color: run.status === 'completed' ? 'var(--color-cat-testing)' : 'var(--color-muted)' }}>
                {run.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
