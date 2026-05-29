interface RiskGaugeProps {
  score: number;
}

function riskColor(score: number): string {
  if (score >= 0.7) return 'var(--color-severity-critical)';
  if (score >= 0.4) return 'var(--color-severity-high)';
  return 'var(--color-cat-testing)';
}

export default function RiskGauge({ score }: RiskGaugeProps) {
  const pct = Math.round(score * 100);

  return (
    <div className="flex items-center gap-2">
      <div
        className="h-2 rounded-full overflow-hidden"
        style={{ backgroundColor: 'var(--color-paper-3)', width: '6rem' }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            backgroundColor: riskColor(score),
            transition: 'width var(--dur-short) var(--ease-out)',
          }}
        />
      </div>
      <span className="text-xs font-outlier tabular-nums" style={{ color: 'var(--color-muted)' }}>
        {pct}%
      </span>
    </div>
  );
}
