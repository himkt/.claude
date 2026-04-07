# Bash Command

Shell operators break `permissions.allow` matching in settings.json — every Bash call must be standalone.

- NEVER chain with `&&` or `;` — one command per Bash tool call
- NEVER `cd /path && command` — `cd` is a separate call (CWD persists between calls)
- NEVER use redirects `>` `>>` `<` — write files via the Write tool
- NEVER use command substitution `$()` or backticks unless unavoidable

## Use dedicated tools (these Bash commands are denied)

| Bash | Use | Note |
|---|---|---|
| `find` | Glob | |
| `ls`, `tree` | Glob | Read for single-dir inspection |
| `grep`, `rg` | Grep | |
| `cat`, `head`, `tail` | Read | Supports `offset`/`limit` |
| `sed`, `awk` | Edit | |
| `mkdir`, `touch` | Write | Auto-creates parents. Exception: `.keep` for dirs needed before non-Write tools |
| `echo`, `printf` | Write (files) or direct output (chat) | |

For broader codebase navigation beyond Glob/Grep, use the Agent tool with `subagent_type=Explore`.
