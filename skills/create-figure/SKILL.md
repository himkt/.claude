---
name: create-figure
description: >
  Create data visualizations and charts using matplotlib. Triggered when user
  asks to create a chart, plot, graph, or visualize data. Also invokable via
  /create-figure. Do NOT use plt.show() — always save to PNG files.
---

# Create Figure

Generate matplotlib-based charts and figures. Write a Python script on the project side, execute it via `uv run` from `~/.claude`, and produce static PNG output.

## Execution Flow

```
User request (e.g., "plot sales.csv as a bar chart")
  │
  ├─ 1. Write Python script to PROJECT directory
  │     e.g., /path/to/project/sales_chart.py
  │
  ├─ 2. cd ~/.claude
  │
  ├─ 3. uv run /path/to/project/sales_chart.py
  │
  └─ 4. PNG output appears in PROJECT directory
        e.g., /path/to/project/sales_chart.png
```

## Script Template Pattern

Every generated script MUST follow this pattern:

```python
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# __file__-based path resolution
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

# Data input (relative to script location)
data_path = SCRIPT_DIR / "data.csv"

# ... chart creation logic ...

# Output (relative to script location)
output_path = SCRIPT_DIR / "chart.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {output_path}")
```

## Key Rules

| Rule | Detail |
|------|--------|
| Backend | Always set `matplotlib.use("Agg")` before importing `pyplot` (headless rendering) |
| Path resolution | All file paths (input data, output images) use `pathlib.Path(__file__).resolve().parent` |
| Output format | PNG only, with `dpi=150` and `bbox_inches="tight"` as defaults |
| No interactive display | Never call `plt.show()` — always use `plt.savefig()` |
| Resource cleanup | Always call `plt.close()` after saving |
| Multiple charts | Combine into a single script; use `plt.figure()` or `plt.subplots()` for each |
| Script location | Always on the PROJECT side (user's working directory), never in `~/.claude` |
| Execution | `cd ~/.claude` then `uv run <absolute-path-to-script>` as separate Bash calls |
| Data sources | CSV/JSON files in the project directory, or inline data from web search / user input |
| Script naming | Descriptive name based on content (e.g., `monthly_revenue_chart.py`), no fixed convention |

## Data Handling Patterns

### CSV files

```python
import csv

data_path = SCRIPT_DIR / "sales.csv"
with open(data_path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
```

### JSON files

```python
import json

data_path = SCRIPT_DIR / "metrics.json"
with open(data_path) as f:
    data = json.load(f)
```

### Inline data (from web search or user input)

```python
# Data gathered by Claude, embedded directly
categories = ["Q1", "Q2", "Q3", "Q4"]
values = [120, 185, 240, 310]
```

## Execution Pattern

IMPORTANT: Execute the script as two separate Bash calls. Do NOT chain with `&&`.

1. `cd ~/.claude`
2. `uv run /absolute/path/to/project/script.py`

The first call changes directory to `~/.claude` where `pyproject.toml` and the `uv`-managed environment live. The second call runs the script using its absolute path so the output lands in the project directory.

## Out of Scope

- Libraries beyond matplotlib (no seaborn, plotly, etc.)
- Interactive charts or `plt.show()`
- GUI or web-based visualization
- Automated data analysis / statistical inference
