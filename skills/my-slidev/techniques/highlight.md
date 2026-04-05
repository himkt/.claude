# Highlight Component

The `<Highlight>` component applies a marker-style background + colored text to inline content. Use it to visually emphasize key terms, numbers, or short phrases within a sentence.

## Types

| Type | Background | Text Color | Use For |
|------|-----------|------------|---------|
| `primary` | Blue tint | Blue (`--c-primary`) | Key terms, important numbers, default |
| `positive` | Green tint | Green (`--c-positive`) | Positive trends, growth, improvements |
| `negative` | Red tint | Red (`--c-negative`) | Negative trends, decline, risks |
| `accent` | Orange tint | Orange (`--c-accent`) | Warnings, items needing attention |
| `important` | Purple tint | Purple (`--c-important`) | Critical points, must-know items |

## Syntax

```md
Revenue grew <Highlight type="positive">+99.3%</Highlight> year-over-year
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `type` | String | `'primary'` | One of: `primary`, `positive`, `negative`, `accent`, `important` |

## Examples

### Key Metrics

```md
- Revenue grew <Highlight type="positive">+99.3%</Highlight> year-over-year
- Margin dropped to <Highlight type="negative">37.4%</Highlight> from 59.1%
- Target price: <Highlight>¥16,000</Highlight>
- Tariff risk rated <Highlight type="accent">High</Highlight>
```

### In a Bullets Slide

```md
---
layout: bullets
---

::header::

# Quarterly Performance

::default::

- Q3 revenue reached <Highlight>¥806.3B</Highlight> (+86% YoY)
- Operating margin improved to <Highlight type="positive">19.25%</Highlight>
- Memory costs surged <Highlight type="negative">+41%</Highlight> in 3 months
- Full-year progress rate at 81.2%
```

### In a Table

```md
| Metric | FY2024 | FY2025 | Change |
|--------|--------|--------|--------|
| Revenue | ¥1.16T | ¥2.25T | <Highlight type="positive">+93%</Highlight> |
| Op. Margin | 24.2% | 16.4% | <Highlight type="negative">-7.8pp</Highlight> |
```

## Color Discipline

Every colored element must have a semantic reason for its color. Never use color for decoration.

| Color | Semantic | When to use | Example |
|-------|----------|-------------|---------|
| `positive` (green) | Good news | Growth, improvement, achievement, gain | Revenue +93%, adoption 84% |
| `negative` (red) | Bad news | Decline, risk, vulnerability, loss, stagnation | Vulnerability 45%, -19% slower |
| `primary` (blue) | Neutral key metric | Quantities without positive/negative connotation | Context window 1M tokens, 5 product forms |
| `accent` (orange) | Caution / noteworthy | Transitional states, mixed signals, items needing attention | -4% (improved but unreliable) |
| `important` (purple) | Critical / structural | Must-know points that don't fit other categories | — |

**Decision flow**: Ask "is this good or bad for the audience?" → Good: `positive`. Bad: `negative`. Neither: `primary`. Mixed/uncertain: `accent`.

## Highlight vs Span Utility Classes

| Technique | Visual Effect | Best For |
|-----------|--------------|----------|
| `<Highlight>` | Background + colored text + bold | The single most important data point on a slide |
| `<span class="c-...">` | Colored text only | All other colored emphasis |
| `<Highlight>` + `**bold**` | Not needed — Highlight already applies `font-weight: 600` | — |

**Rules:**

1. **Maximum 1 `<Highlight>` per slide.** This is the number the audience should remember.
2. **Use `<span class="c-...">` for all other emphasis.** Same color semantics apply.
3. **Same color semantics for both.** `<Highlight type="positive">` and `<span class="c-positive">` follow the same color discipline table above.
4. **Stats/KPI slides are the exception.** On `stats-grid` or KPI-style table layouts where multiple large numbers are presented equally, `<Highlight>` is not used — each number uses `<span class="c-...">` with its semantic color.
