---
name: base-dir
description: >
  Resolve the base directory for output files. Loaded by consuming skills
  via Skill(base-dir) when they need to determine where to write output.
  Do NOT invoke this skill directly — consuming skills load it automatically.
---

# Base Directory Resolution

Canonical procedure for determining the base directory for output files.

## When to Skip This Procedure

Each consuming skill defines its own **inference rules** for when the base
directory can be reliably determined without user interaction. Common cases:

- The skill's argument is an absolute path (starts with `/`)
- The context unambiguously determines the base (e.g., no path argument
  and CWD is a project directory, not `~/.claude`)

When inference succeeds, the consuming skill skips this procedure entirely.
When inference fails, the consuming skill follows the procedure below.

## Procedure

### Step 1: Interactive Selection

Use `AskUserQuestion` with the following configuration:

**Question**: `"Select the base directory for output files:"`

**Options** (apply context-dependent recommended label based on CWD):

| Option | Label when CWD = `~/.claude` | Label when CWD ≠ `~/.claude` |
|--------|------------------------------|------------------------------|
| 1 | `{cwd}/` | `{cwd}/ (recommended)` |
| 2 | `/tmp/claude-code/ (recommended)` | `/tmp/claude-code/` |
| 3 | `Other` | `Other` |

Option 3 ("Other") uses `AskUserQuestion`'s built-in free-text input — the
user types a custom path directly in the same prompt. No second
`AskUserQuestion` call is needed.

### Step 2: Resolution

Resolve the selected option to an absolute base path:

| Selection | Resolution |
|-----------|-----------|
| Option 1 | `base = {cwd}` (resolved to absolute path) |
| Option 2 | `base = /tmp/claude-code` |
| Option 3 (free text) | `base = user's input` (resolved to absolute path; if relative, resolve against CWD) |

The consuming skill uses the resolved `base` for its own path computation.
