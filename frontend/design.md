# Design — PRLens

A locked design system for this app. Every page redesign reads this file before
emitting code. Do not regenerate per page — extend or amend this file when the
system needs to grow.

## Genre
modern-minimal

## Macrostructure family
All pages: Workbench (app dashboard). Pages are content-first with stat cards
and finding lists. No enrichment — function carries the page.

## Theme — deep indigo dev tool

```css
:root {
  --color-paper:        oklch(12% 0.006 264);
  --color-paper-2:      oklch(16% 0.007 264);
  --color-paper-3:      oklch(20% 0.007 264);
  --color-rule:         oklch(24% 0.006 264);
  --color-rule-subtle:  oklch(20% 0.005 264);
  --color-ink:          oklch(92% 0.005 264);
  --color-ink-2:        oklch(72% 0.005 264);
  --color-muted:        oklch(48% 0.005 264);
  --color-accent:       oklch(68% 0.18 280);
  --color-accent-dim:   oklch(48% 0.12 280);
  --color-focus:        oklch(74% 0.20 280);
}
```

## Typography
- Display: Geist, weight 500–600, tracking -0.02em
- Body: Geist, weight 400
- Outlier: Geist Mono, weight 400 (PR numbers, percentages, file paths)

## Spacing
4-point named scale. Pages must use named tokens (`var(--space-md)`), never raw
values.

## Motion
- Easings: `--ease-out` cubic-bezier(0.16, 1, 0.3, 1)
- No reveals, no animate-on-scroll. The page is composed.

## Microinteractions stance
- Silent success — no celebratory toasts
- Hover: border-color shift on interactive cards
- Focus: 2px ring, instant appearance

## CTA voice
- Buttons: pill-rounded, outlined style
- Primary action colour: accent on borders and labels, never filled backgrounds

## Nav
N5 Floating pill — content-sized pill tabs, backdrop-blur, soft separation.
Active item gets paper-3 background.

## Footer
Ft2 Inline single line — none in this dashboard app. Footer is omitted;
the nav carries the full navigation surface.

## Per-page allowances
- Dashboard: stat cards in 3-column grid, empty-state prompt
- PR List: row links with hover border shift
- PR Detail: stacked finding cards with severity badges
- Evaluation: empty-state prompt

## What pages MUST share
- The indigo accent colour and its placement (≤ 3% per viewport)
- Geist display + Geist body fonts
- Pill-shaped severity badges and nav items
- Card border colour `--color-rule-subtle`, hover shift to `--color-rule`

## What pages MAY differ on
- Page heading copy and lede text
- Grid layouts (3-column stats, single-column findings list)
