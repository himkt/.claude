## Overview

This is the `~/.claude` configuration directory.
Since Claude Code treats `~/.claude/CLAUDE.md` as global settings, this repository has a unique CLAUDE.md structure:

- `CLAUDE.md` (root) → Global settings for all projects
- `.claude/CLAUDE.md` (this file) → Settings specific to this repository

**What goes where:**
- Global: Cross-project settings, custom agent/command/skill descriptions, personal preferences
- Project: Repository structure, project-specific conventions

**Rule:** "Needed in other projects?" → Yes: global, No: project

## Directory Structure

- `bin/status.py` - Status line display (model, directory, token usage with color coding)
- `design-docs/` - Design documents in `{slug}/design-doc.md` subdirectories. **Gitignored** — never tracked.
- `vendor/` - Third-party repositories managed as git submodules (e.g., `vendor/slidev`)
- `rules/` - User-level rule files auto-loaded into context for all projects
