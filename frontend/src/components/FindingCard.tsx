interface FindingCardProps {
  finding: {
    id: number;
    file_path: string;
    line_start?: number;
    severity: string;
    category: string;
    message: string;
    suggestion?: string;
    confidence: number;
  };
}

const severityVars: Record<string, string> = {
  critical: 'var(--color-severity-critical)',
  high:     'var(--color-severity-high)',
  medium:   'var(--color-severity-medium)',
  low:      'var(--color-severity-low)',
};

const categoryVars: Record<string, string> = {
  security:       'var(--color-cat-security)',
  reliability:    'var(--color-cat-reliability)',
  performance:    'var(--color-cat-performance)',
  maintainability: 'var(--color-cat-maintainability)',
  testing:        'var(--color-cat-testing)',
};

export default function FindingCard({ finding }: FindingCardProps) {
  const sevColor = severityVars[finding.severity] || 'var(--color-muted)';
  const catColor = categoryVars[finding.category] || 'var(--color-muted)';

  return (
    <div
      className="rounded-card p-5"
      style={{
        backgroundColor: 'var(--color-paper-2)',
        border: '1px solid var(--color-rule-subtle)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span
          className="inline-block px-2.5 py-0.5 rounded-pill text-xs font-semibold"
          style={{ backgroundColor: sevColor, color: '#fff' }}
        >
          {finding.severity.toUpperCase()}
        </span>
        <span className="text-xs font-medium" style={{ color: catColor }}>
          {finding.category}
        </span>
        <span className="text-xs ml-auto font-outlier tabular-nums" style={{ color: 'var(--color-muted)' }}>
          {(finding.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <p className="text-sm mb-1.5" style={{ color: 'var(--color-ink)' }}>
        {finding.message}
      </p>
      <p className="text-xs mb-3 font-outlier" style={{ color: 'var(--color-ink-2)' }}>
        {finding.file_path}{finding.line_start ? `:${finding.line_start}` : ''}
      </p>
      {finding.suggestion && (
        <div
          className="pt-3 mt-1 text-xs"
          style={{ borderTop: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink-2)' }}
        >
          <span className="font-medium" style={{ color: 'var(--color-accent)' }}>Suggestion</span>
          <span className="ml-1.5">{finding.suggestion}</span>
        </div>
      )}
    </div>
  );
}
