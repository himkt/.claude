# Git Workflow

- Commit message: single-line English with conventional prefix (`feat`/`fix`/`chore`/`refactor`/`docs`). NEVER multi-line, NEVER HEREDOC, always `git commit -m "..."`
- NEVER `git -C <path>` — breaks `permissions.allow` matching in settings.json; CWD is already the project root
- NEVER `git add -f` / `--force` — gitignored files stay gitignored
- NEVER commit from `design-docs/` or `researches/` (globally gitignored)
