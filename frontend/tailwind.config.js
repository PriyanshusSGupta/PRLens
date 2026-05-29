/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper:   'var(--color-paper)',
        'paper-2': 'var(--color-paper-2)',
        'paper-3': 'var(--color-paper-3)',
        rule:    'var(--color-rule)',
        'rule-subtle': 'var(--color-rule-subtle)',
        ink:     'var(--color-ink)',
        'ink-2': 'var(--color-ink-2)',
        muted:   'var(--color-muted)',
        accent:  'var(--color-accent)',
        'accent-dim': 'var(--color-accent-dim)',
        focus:   'var(--color-focus)',
      },
      fontFamily: {
        display: ['"Geist"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        body:    ['"Geist"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        outlier: ['"Geist Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card: 'var(--radius-card)',
        pill: 'var(--radius-pill)',
        input: 'var(--radius-input)',
      },
      spacing: {
        '3xs': 'var(--space-3xs)',
        '2xs': 'var(--space-2xs)',
        xs:    'var(--space-xs)',
      },
    },
  },
  plugins: [],
};
