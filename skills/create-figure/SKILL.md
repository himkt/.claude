---
name: create-figure
description: >
  Create data visualizations and charts using matplotlib. Triggered when user
  asks to create a chart, plot, graph, or visualize data. Also invokable via
  /create-figure. Do NOT use plt.show() — always save to PNG files.
---

# Create Figure

Generate matplotlib charts. Scripts and outputs go in the project directory.
Only the execution borrows the uv environment from `~/.claude`.

## Procedure

### 1. Create the script in the project directory

Use the Write tool to create a `.py` file in the user's working directory (the project).
Never create scripts in `~/.claude`.

The script must follow this pattern:

```python
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

# Data input (relative to script location)
data_path = SCRIPT_DIR / "data.csv"

# Create the figure
fig, ax = plt.subplots()
# ... plotting logic ...

# Output (relative to script location)
output_path = SCRIPT_DIR / "chart.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {output_path}")
```

Key points:
- `matplotlib.use("Agg")` must come before importing `pyplot`
- All paths use `pathlib.Path(__file__).resolve().parent`. This ensures inputs and outputs stay in the project directory regardless of where the script is executed from
- Never call `plt.show()`. Save to PNG with `plt.savefig()`
- Always call `plt.close()` after saving
- Default output: PNG, `dpi=150`, `bbox_inches="tight"`
- For multiple charts, combine into one script using `plt.figure()` or `plt.subplots()`

### 2. Execute the script

`~/.claude` has a `pyproject.toml` that manages matplotlib via uv.
Run two **separate** Bash calls to use this environment (`&&` chaining is forbidden):

```
cd ~/.claude
```

```
uv run /absolute/path/to/project/script.py
```

The absolute path ensures output is written to the project directory.

### 3. Verify the result

Use the Read tool to load the output PNG and show it to the user.

## Data handling

CSV:
```python
import csv
with open(SCRIPT_DIR / "sales.csv") as f:
    rows = list(csv.DictReader(f))
```

JSON:
```python
import json
with open(SCRIPT_DIR / "metrics.json") as f:
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
