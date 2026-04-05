---
name: create-figure
description: >
  Create data visualizations and charts using matplotlib. Triggered when user
  asks to create a chart, plot, graph, or visualize data. Also invokable via
  /create-figure. Do NOT use plt.show() — always save to PNG files.
---

# Create Figure

Generate matplotlib charts. Scripts, outputs, and data go in separate subdirectories under `figures/`.
Only the execution borrows the uv environment from `~/.claude`.

**Before writing any script, read the Chart Type Selection and Color Rules sections.** All charts in a deck share the same `C_BAR` / `C_BAR_SEC` palette regardless of data topic.

## Procedure

### 0. Resolve directories

If `${FIGURE_BASE}` is already set by the calling context (e.g., a research skill passes its project folder), use it as `${BASE}` and skip base-dir resolution.

Otherwise: Load `Skill(base-dir)` and follow its procedure (no path argument; CWD-based inference applies).
If the resolved `${BASE}` is `~/.claude`, override to `${BASE} = /tmp/claude-code`.

Set `${SRC_DIR} = ${BASE}/figures/src`.
Set `${OUTPUT_DIR} = ${BASE}/figures/output`.
Set `${DATA_DIR} = ${BASE}/figures/data`.

Create the directories if they do not exist.
All subsequent steps use `${SRC_DIR}`, `${OUTPUT_DIR}`, and `${DATA_DIR}` instead of CWD for file creation. Never create scripts or outputs in `~/.claude`.

**Font:** No setup needed. The theme font `Noto Sans` is available as a system font. Scripts set `plt.rcParams['font.family'] = 'Noto Sans'` (see template below).

### 1. Create the script

Use the Write tool to create a `.py` file in `${SRC_DIR}`.

The script must follow this pattern:

```python
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = pathlib.Path("${OUTPUT_DIR}")   # filled in by skill
DATA_DIR = pathlib.Path("${DATA_DIR}")       # filled in by skill

plt.rcParams['font.family'] = 'Noto Sans'

# Data input
data_path = DATA_DIR / "data.csv"

# Create the figure
fig, ax = plt.subplots()
# ... plotting logic ...

# Output — filename matches script name
script_stem = pathlib.Path(__file__).stem
output_path = OUTPUT_DIR / f"{script_stem}.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor='white')
plt.close()
print(f"Saved: {output_path}")
```

Key points:
- **All figure text in English** — matplotlib defaults don't support CJK; use English for labels/titles/legends
- **No `ax.set_title()`** — when embedded in slides, the slide heading is the title
- `matplotlib.use("Agg")` before `import matplotlib.pyplot`
- Output filename matches script name (`chart.py` → `chart.png`)
- Never `plt.show()`, always `plt.savefig()` then `plt.close()`
- PNG, `dpi=150`, `bbox_inches="tight"`, `facecolor='white'`

### 2. Execute the script

`~/.claude` has a `pyproject.toml` that manages matplotlib via uv.
Run a single Bash call with `--frozen` and `--project` to use this environment without changing CWD:

```
uv run --frozen --project ~/.claude ${SRC_DIR}/script_name.py
```

`--frozen` prevents lockfile updates. `--project ~/.claude` uses `~/.claude/.venv` without changing CWD.

### 3. Verify the result

Use the Read tool to load the output PNG from `${OUTPUT_DIR}` and show it to the user.

## Data handling

CSV:
```python
import csv
with open(DATA_DIR / "sales.csv") as f:
    rows = list(csv.DictReader(f))
```

JSON:
```python
import json
with open(DATA_DIR / "metrics.json") as f:
    data = json.load(f)
```

Inline data (from web search or user input):
```python
categories = ["Q1", "Q2", "Q3", "Q4"]
values = [120, 185, 240, 310]
```

## Chart Type Selection

Pick the right visualization for the data. Do NOT default to bar charts for everything.

| Data pattern | Chart type | matplotlib |
|---|---|---|
| Category comparison, ranking | Horizontal bar | `ax.barh()` |
| Time series, trend | Line chart | `ax.plot()` |
| Correlation between 2 variables | Scatter plot | `ax.scatter()` |
| Distribution of one variable | Histogram | `ax.hist()` |
| Distribution comparison across groups | Box plot or violin plot | `ax.boxplot()` / `ax.violinplot()` |
| Matrix, cross-tabulation | Heatmap | `ax.imshow()` + annotate |
| Part-of-whole composition | Stacked bar | `ax.bar(bottom=...)` |
| Before/after, paired comparison | Dumbbell chart | `ax.hlines()` + `ax.scatter()` |
| Time-based categories (quarters, years) | Vertical bar | `ax.bar()` |

**Horizontal vs vertical bars**: Prefer `barh` when category labels are text. Use vertical `bar` only for time-based x-axes.

## Color Rules

**1 chart = max 2 colors.** This is the single most important design rule. Violating it produces amateurish, noisy charts.

### Allowed palette

These correspond to the Slidev theme's CSS tokens in `skills/my-slidev/theme/styles/index.css`. When updating colors, change both.

```python
# Primary (use for most bars/lines)
C_BAR = '#3B82F6'         # blue-500

# Muted secondary (use for secondary series, negative values, or contrast)
C_BAR_SEC = '#94A3B8'     # slate-400

# Accent (use for ONE highlighted item only — never for multiple bars)
C_ACCENT = '#1E40AF'      # blue-800 (darker shade of primary)

# Negative accent (use only when one specific item is the "worst")
C_NEGATIVE = '#DC2626'    # red-600

# Spine / grid
C_TEXT = '#1E293B'
C_TEXT_SEC = '#64748B'
C_GRID = '#E2E8F0'
```

### Decision table

| Data pattern | Colors to use |
|---|---|
| Single series, all same type | `C_BAR` for all |
| Single series, grouping by category | Lightness steps of blue (`#1E40AF` / `#3B82F6` / `#93C5FD`) |
| Two series (e.g., Verified vs Pro) | `C_BAR` + `C_BAR_SEC` |
| Positive vs negative values | `C_BAR` (positive) + `C_BAR_SEC` (negative) |
| Highlight one worst item | `C_BAR_SEC` for all + `C_NEGATIVE` for worst |
| Highlight one best/top item | `C_BAR` for all + `C_ACCENT` (darker) for top |

### Prohibited

- **Semantic coloring** — do NOT choose colors based on what the data "means." A vulnerability chart uses `C_BAR` (blue), not red. An adoption chart uses `C_BAR`, not green. Data meaning comes from axis labels and slide context. All charts in a deck must look like they belong together
- **3+ hues in one chart** — never blue + red + green + orange. Use `C_NEGATIVE` or `C_ACCENT` for at most 1 highlighted item; everything else is `C_BAR` or `C_BAR_SEC`
- **`C_NEGATIVE` / `C_POSITIVE` as primary color** — red and green are only for highlighting a single item, never for all data points
- **Different Y-axis scales in small multiples** — side-by-side panels MUST share the same Y-axis range

### Standard axes styling

Apply to every figure:

```python
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color(C_GRID)
ax.spines['bottom'].set_color(C_GRID)
ax.tick_params(colors=C_TEXT_SEC)
ax.yaxis.grid(True, alpha=0.3, color='#CBD5E1')
ax.set_axisbelow(True)
```

Always use `facecolor='white'` in `plt.savefig()`.

## Out of scope

- Libraries beyond matplotlib (no seaborn, plotly, etc.)
- Interactive display via `plt.show()`
- GUI or web-based visualization
- Automated data analysis or statistical inference
