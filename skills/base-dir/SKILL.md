---
name: base-dir
description: >
  Resolve the base directory for output files. Loaded by consuming skills
  via Skill(base-dir). Do NOT invoke directly.
---

# Base Directory Resolution

## Procedure

1. If consuming skill's argument is an absolute path → skip this skill entirely.
2. If `${CWD}` is the user's home directory or its config subdirectory (i.e., not a real project root) → go to step 3.
   Otherwise → `${BASE} = ${CWD}`. Done.
3. Ask via `AskUserQuestion` ("Select the base directory for output files:"):
   - `/tmp/claude-code (recommended)` → `${BASE} = /tmp/claude-code`
   - `${CWD}` → `${BASE} = ${CWD}`
   - `Other` (free text) → `${BASE} = user input` (resolve against `${CWD}` if relative)
