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

# Data input
data_path = DATA_DIR / "data.csv"

# Create the figure
fig, ax = plt.subplots()
# ... plotting logic ...

# Output — filename matches script name
script_stem = pathlib.Path(__file__).stem
output_path = OUTPUT_DIR / f"{script_stem}.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
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

## Out of scope

- Libraries beyond matplotlib (no seaborn, plotly, etc.)
- Interactive display via `plt.show()`
- GUI or web-based visualization
- Automated data analysis or statistical inference
