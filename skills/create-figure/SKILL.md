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

## Procedure

### 0. Resolve directories

Load `Skill(base-dir)` and follow its procedure (no path argument; CWD-based inference applies).
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
- **All text in figures must be in English** — titles, axis labels, legends, annotations, and tick labels. matplotlib's default fonts do not support CJK characters (Japanese, Chinese, Korean), causing them to render as □ (tofu). Even when the report or presentation is in a non-English language, all figure text must be English.
- `matplotlib.use("Agg")` must come before importing `pyplot`
- `OUTPUT_DIR` and `DATA_DIR` are hardcoded absolute paths embedded by the skill at script-generation time. Do not use `pathlib.Path(__file__).resolve().parent`
- Output filenames must match the script name (e.g., `sales_chart.py` → `sales_chart.png`). For multiple outputs from one script, use a `_N` suffix (e.g., `sales_chart_1.png`, `sales_chart_2.png`)
- Never call `plt.show()`. Save to PNG with `plt.savefig()`
- Always call `plt.close()` after saving
- Default output: PNG, `dpi=150`, `bbox_inches="tight"`
- For multiple charts, combine into one script using `plt.figure()` or `plt.subplots()`

### 2. Execute the script

`~/.claude` has a `pyproject.toml` that manages matplotlib via uv.
Run a single Bash call with `--frozen` and `--project` to use this environment without changing CWD:

```
uv run --frozen --project ~/.claude ${SRC_DIR}/script_name.py
```

`--frozen` prevents uv from updating the lockfile. `--project ~/.claude` tells uv to use `~/.claude/pyproject.toml` and `~/.claude/.venv` without changing CWD. The script path under `${SRC_DIR}` ensures the script can be located and executed without relying on CWD; output location is controlled by the hardcoded `OUTPUT_DIR` constant in the script.

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

## Color Rules

**1 chart = max 2 colors.** This is the single most important design rule. Violating it produces amateurish, noisy charts.

### Allowed palette

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

- **3+ different hues in one chart** — never blue + red + green + orange
- **Semantic rainbow** — do NOT assign a different color to each bar "because they mean different things"
- **Full-saturation colors for all bars** — at most 1 bar gets a saturated accent; the rest are muted or same-hue
- **`C_POSITIVE` (`#16A34A` green) in bar charts** — green bars look garish; use blue as the default positive
- **Different Y-axis scales in small multiples** — when panels are side-by-side, all panels MUST share the same Y-axis range. Different scales mislead the reader into comparing bar heights directly. This is a data integrity issue, not just aesthetics

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
