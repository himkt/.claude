---
name: base-dir
description: >
  Resolve the base directory for output files. Loaded by consuming skills
  via Skill(base-dir) when they need to determine where to write output.
  Do NOT invoke this skill directly — consuming skills load it automatically.
---

# Base Directory Resolution

Canonical procedure for determining the base directory for output files.
Consuming skills load this via `Skill(base-dir)`.

## Procedure

### Step 1: Inference

Try to determine the base directory without user interaction, in order:

1. If the consuming skill's argument is an absolute path (starts with `/`) → **skip this entire procedure**. The consuming skill already has a fully-qualified path and does not need a base directory.
2. If CWD ≠ `~/.claude` → set `base = CWD`. Done — skip to the consuming skill's next step.

If neither condition is met, proceed to Step 2.

### Step 2: Interactive Selection

Use `AskUserQuestion` with the following configuration:

**Question**: `"Select the base directory for output files:"`

**Options**:

| Option | Label |
|--------|-------|
| 1 | `{cwd}/` |
| 2 | `/tmp/claude-code/ (recommended)` |

Option 3 ("Other") uses `AskUserQuestion`'s built-in free-text input — the
user types a custom path directly in the same prompt. No second
`AskUserQuestion` call is needed.

### Step 3: Resolution

Resolve the selected option to an absolute base path:

| Selection | Resolution |
|-----------|-----------|
| Option 1 | `base = {cwd}` (resolved to absolute path) |
| Option 2 | `base = /tmp/claude-code` |
| Option 3 (free text) | `base = user's input` (resolved to absolute path; if relative, resolve against CWD) |

The consuming skill uses the resolved `base` for its own path computation.
