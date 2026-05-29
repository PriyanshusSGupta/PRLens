const severityVars: Record<string, string> = {
  critical: 'var(--color-severity-critical)',
  high:     'var(--color-severity-high)',
  medium:   'var(--color-severity-medium)',
  low:      'var(--color-severity-low)',
};

interface SeverityBadgeProps {
  severity: string;
}

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const bg = severityVars[severity] || 'var(--color-muted)';

  return (
    <span
      className="inline-block px-2.5 py-0.5 rounded-pill text-xs font-semibold"
      style={{ backgroundColor: bg, color: '#fff' }}
    >
      {severity.toUpperCase()}
    </span>
  );
}
