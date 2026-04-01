---
name: design-doc-execute
description: Implement features based on a design document with automatic validation and fixing. Use when the user asks to implement or execute a design document. Takes document path as argument. Teammates must always load skills using the Skill tool, not by reading skill files directly. Do NOT implement a design document by reading it and coding manually — always invoke this skill instead.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, WebSearch, WebFetch
---

# Design Doc Execute (Agent Teams Edition)

Implement features based on a design document using up to four roles: Director (orchestrator), Programmer (implements), Tester (writes tests), and Verifier (E2E/integration testing). The Director judges which teammates to spawn based on the nature of the implementation tasks. For each step, the Tester writes unit tests first, the Director reviews and approves them, then the Programmer implements code to pass the tests. The Director also reviews the Programmer's implementation for code quality and design doc compliance before committing. After all TDD steps, the Verifier performs E2E/integration verification (Phase D) if spawned.

| Role | Agent | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Spawn teammates, validate doc, assign steps, review tests against design doc, review implementation code for quality and compliance, commit after each phase, escalation arbitration, orchestrate TDD cycle | Write code, write tests | [roles/director.md](roles/director.md) |
| **Programmer** | `design-doc-executor` | Implement code to pass tests, run tests, report results, escalate test defects to Director, update design doc checkboxes and Progress counter | Write or modify tests, commit code, communicate with user directly | [roles/programmer.md](roles/programmer.md) |
| **Tester** | `design-doc-tester` | Read design doc, write unit tests per step, fix tests based on Director feedback, report to Director | Write implementation code, commit code, communicate with user directly | [roles/tester.md](roles/tester.md) |
| **Verifier** | `design-doc-verifier` | E2E/integration testing, tool discovery, evidence collection (screenshots, logs, output), failure reporting with suggested fixes | Write code, write tests, commit, communicate with user directly | [roles/verifier.md](roles/verifier.md) |

## Architecture

Only the lead (Director) can spawn teammates (no nested teams). The Director decides which teammates to spawn based on task analysis (see [roles/director.md](roles/director.md)). They work together through each step using a TDD workflow, optionally followed by E2E verification.

```
User
 +-- Director (Main Claude -- creates team, validates doc, assigns steps, reviews tests & code, obtains user approval, commits, orchestrates)
      +-- Programmer (teammate -- design-doc-executor agent, implements code to pass tests)
      +-- Tester (teammate -- design-doc-tester agent, writes unit tests per step)
      +-- Verifier (teammate -- design-doc-verifier agent, E2E/integration testing)
```

- **Director <-> Programmer**: team messaging (step assignments, test results, code review feedback, escalation)
- **Director <-> Tester**: team messaging (step assignments, test review feedback, test defect reports)
- **Director <-> Verifier**: team messaging (verification assignments, results, failure routing)
- **Director**: git operations (commit after each phase — tests and implementation separately)

## Process

### Step 1: Resolve Design Document Path (Director)

Before validation, resolve `$ARGUMENTS` into a concrete `design-doc.md` path using a three-tier detection strategy, evaluated in order:

| Tier | Condition | Action |
|:--|:--|:--|
| 1 — Direct file path | `$ARGUMENTS` ends with `design-doc.md` | Use as-is (current behavior) |
| 2 — Slug directory | `$ARGUMENTS` is a directory that contains `design-doc.md` directly | Append `/design-doc.md` and use as direct path |
| 3 — Base directory | `$ARGUMENTS` is a directory containing `*/design-doc.md` (one level deep) | Enter discovery flow (see below) |

**Tier evaluation is sequential and short-circuits**: once a tier matches, later tiers are not evaluated.

#### Discovery Flow (Tier 3)

When the base directory tier matches:

1. **Discover**: Use Glob to find all `*/design-doc.md` files one level deep under the base directory.
2. **Read Status**: For each discovered file, read the `**Status**:` field from the document header.
3. **Filter**: Keep only documents with `Status: Approved`. Documents with any other status (`Draft`, `In Progress`, `Complete`) are excluded.
4. **Branch by count**:

| Count | Behavior |
|:--|:--|
| 0 | Error and abort (see Error: Zero Approved below) |
| 1 | Auto-select: proceed with this document directly |
| 2–4 | Present options via `AskUserQuestion` (see Selection UI below) |
| 5+ | Present options via paginated `AskUserQuestion` (see Pagination below) |

#### Selection UI (2–4 Approved Docs)

Use `AskUserQuestion` with one question. Each option label is the slug name (directory name) of the design doc. The built-in "Other" option is always available for the user to type a direct path or cancel.

Example with 3 approved docs:

```
Question: "Which design document would you like to implement?"
Options:
  1: "feature-auth"
  2: "refactor-db-layer"
  3: "add-cli-export"
  (Other is added automatically)
```

#### Pagination (5+ Approved Docs)

When there are more than 4 approved docs, `AskUserQuestion`'s option limit (max 4) is exceeded. Use pagination with all options sorted alphabetically by slug:

- **Non-last page**: Show 3 options + a 4th option labeled `"More..."`.
- **Last page rule**: If remaining items after the current page would be ≤ 4, show all remaining items directly (no `"More..."` needed). This avoids a last page with only 1 option, which would violate `AskUserQuestion`'s minimum of 2 options per question.
- Continue until the user selects a document or uses "Other".

Example with 7 approved docs: page 1 shows 3 + "More..." (4 remain), page 2 shows all 4. Example with 5: page 1 shows 3 + "More..." (2 remain), page 2 shows both 2.

#### Error: Zero Approved Docs

When design docs exist but none have `Status: Approved`, display a message listing all found docs with their current statuses so the user understands why none qualified. Format:

```
No approved design documents found in <base-directory>.

Found documents:
  - <slug-1>/design-doc.md — Status: Draft
  - <slug-2>/design-doc.md — Status: In Progress
  - <slug-3>/design-doc.md — Status: Complete

Only documents with Status: Approved can be executed. Update the status or specify a direct path.
```

Then abort (do not proceed to team creation or execution).

#### Error: Invalid Path

When `$ARGUMENTS` does not match any of the three tiers (not a file path ending in `design-doc.md`, not a directory containing `design-doc.md`, and no `*/design-doc.md` found underneath), display:

```
Invalid argument: <$ARGUMENTS>
Expected one of:
  - Path to a design-doc.md file (e.g., design-docs/my-feature/design-doc.md)
  - Slug directory containing design-doc.md (e.g., design-docs/my-feature/)
  - Base directory containing */design-doc.md (e.g., design-docs/)
```

Then abort.

After resolution, the resolved path is used as the design document path for all subsequent steps.

### Step 2: Validate Design Document & Create Branch (Director)

Before creating any team:

1. Read the design document completely.
2. Check for `COMMENT(` markers using Grep. If found, resolve them directly: apply the requested changes and remove the markers. Verify with Grep that no `COMMENT(` markers remain before proceeding.
3. Check for `FIXME(claude)` markers in the codebase using Grep. If found, note them for the Programmer to resolve first.
4. Determine the step order and total number of steps.
5. **Create a feature branch if on the default branch.** Get the default branch with `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` and the current branch with `git branch --show-current`. If they match, use `AskUserQuestion` to propose the branch name `feat/<design-doc-slug>` and ask the user to approve before creating it. The user will create the branch themselves or approve the proposed name. If already on a non-default branch, skip this step.

### Step 3: Create Team & Spawn Teammates (Director)

Create an agent team and spawn the teammates needed for this project. Analyze the implementation tasks to decide which roles to spawn (see [roles/director.md](roles/director.md) for team composition guidelines).

**Programmer spawn prompt:**

```
You are the Programmer in a design document execution team.

Load the design-doc skill using: Skill(design-doc)
Read your role definition at: roles/programmer.md

DESIGN DOCUMENT: [INSERT DESIGN DOC PATH]

IMPORTANT: Do NOT commit code yourself. The Director handles all git operations.
IMPORTANT: If blocked, message the Director immediately instead of assuming.
IMPORTANT: Read and follow rules/bash-command.md for all Bash commands.

Start by reading the design document. Then wait for the Director to assign your first step.
```

**Tester spawn prompt:**

```
You are the Tester in a design document execution team.

Load the design-doc skill using: Skill(design-doc)
Read your role definition at: roles/tester.md

DESIGN DOCUMENT: [INSERT DESIGN DOC PATH]

IMPORTANT: Do NOT commit code yourself. The Director handles all git operations.
IMPORTANT: Do NOT write implementation code — only test code.
IMPORTANT: If blocked, message the Director immediately instead of assuming.
IMPORTANT: Read and follow rules/bash-command.md for all Bash commands.

Start by reading the design document. Then wait for the Director to assign your first step.
```

**Verifier spawn prompt:**

```
You are the Verifier in a design document execution team.

Load the design-doc skill using: Skill(design-doc)
Read your role definition at: roles/verifier.md

DESIGN DOCUMENT: [INSERT DESIGN DOC PATH]

IMPORTANT: Do NOT commit code or modify implementation/test files.
IMPORTANT: If blocked, message the Director immediately instead of assuming.
IMPORTANT: Read and follow rules/bash-command.md for all Bash commands.

Start by reading the design document and discovering available tools.
Then wait for the Director to assign your first verification task.
```

See [roles/director.md](roles/director.md) for commit message conventions.

### Step 4: Execute Steps with Per-Step TDD Cycle (Director)

For each step in the design document:

#### Phase A: Test Writing

1. **Assign**: Message the Tester with the step number, description, and specification.
2. **Wait for Tester**: Tester reads spec, writes tests, reports. If test framework is ambiguous, ask user via `AskUserQuestion` and relay.
3. **Review tests** against the design doc. Send feedback until satisfied.
4. **Commit tests** (separate commands, do NOT chain with `&&`):
   - `git add <test-files>`
   - `git commit -m "test: add tests for [feature description]"`

#### Phase B: Implementation

1. **Assign**: Message the Programmer with step number, description, and test file paths.
2. **Wait for Programmer**: Programmer implements, runs tests, reports. On suspected test defect, see [roles/director.md](roles/director.md) for the escalation protocol.
3. **Programmer updates design doc**: Checkboxes, timestamps, and Progress counter.

#### Phase C: Code Review (Director)

1. **Review**: Verify code matches design doc, quality is acceptable, no unnecessary changes.
2. **Feedback loop**: Send feedback if issues found. Programmer fixes, re-runs tests, re-reports. Repeat until satisfied.
3. **Commit implementation** (separate commands, do NOT chain with `&&`):
   - `git add <files> <design-doc>`
   - `git commit -m "feat: [description of what was implemented]"`

Repeat from Phase A for the next step. Always include the design document in the implementation commit.

**On-Demand Verification**: Any teammate can request verification mid-task via the Director. The Director decides whether to route immediately or defer:

| Route immediately | Defer to Phase D |
|:--|:--|
| User-visible behavior change (UI, CLI output, API response) | Internal refactoring or data model change |
| Integration with external system | Adequately covered by unit tests |
| Behavior difficult to catch with unit tests alone | Verification requires setup from a later step |

### Phase D: Verification (Director) — conditional

**Skip this phase entirely if the Verifier was not spawned.** Proceed directly to Step 5 (User Approval).

If the Verifier was spawned, assign verification:

1. Send the Verifier the design document, completed steps, and relevant files.
2. Verifier discovers tools, executes E2E verification, captures evidence, reports results.
3. **Route failures**: Implementation bugs → Programmer, test gaps → Tester, spec issues → user.
4. Re-verify after fixes. Proceed to User Approval when all verifiable criteria pass.

### Step 5: User Approval (Director)

After all TDD steps complete but before finalization, present the implementation to the user for approval.

#### Success Criteria Verification

**Before presenting to the user**, verify the design document's Success Criteria section:

1. Read the `## Success Criteria` section from the design document.
2. For each criterion, verify it is satisfied by inspecting the implementation (grep, read files, run tests as needed).
3. Check off all satisfied criteria in the design document (`- [ ]` → `- [x]`).
4. If any criterion is NOT satisfied, resolve it before proceeding to user approval — route to Programmer or Tester as needed.

This step is **mandatory** and must not be skipped.

#### Change Presentation

1. **Git diff command** for the user to inspect (e.g., `git diff main...HEAD`).
2. **Step-by-step change summary** — concise prose of what changed per step (files modified, key behaviors).

#### Approval Interaction

Use `AskUserQuestion`:

| Option | Label | Description | Behavior |
|:--|:--|:--|:--|
| 1 | **Approve** | Proceed with the current result | Proceed to finalization (Step 6) |
| 2 | **Scan for COMMENT markers** | Add `COMMENT(name): feedback` markers to the changed source files, then select this option to process them | Scan and process markers (see Revision Loop below) |
| 3 | *(Other — built-in)* | *(Free text input)* | Interpret user intent (see Revision Loop below) |

See [roles/director.md](roles/director.md) for user interaction rules (COMMENT handling, classification, intent judgment, abort detection).

#### Revision Loop (COMMENT Marker-Based Feedback)

When the user selects "Scan for COMMENT markers": scan changed files for `COMMENT(` markers. Classify by file location (see [roles/director.md](roles/director.md)) and route: design doc COMMENTs → Director resolves directly; source file → Programmer; test file → Tester. After all COMMENTs are resolved and verified, re-present to user.

When the user selects "Other": interpret intent per [roles/director.md](roles/director.md) rules.

No round limit — the loop continues until the user approves or aborts.

#### Abort Flow

1. Update design document Status to "Aborted", add Changelog entry.
2. Commit (separate commands): `git add <design-doc>` then `git commit -m "docs: mark design doc as aborted"`
3. Shut down teammates and clean up the team.

### Step 6: Finalize & Clean Up (Director)

1. Update design document Status to "Complete" and add final Changelog entry.
2. Commit (separate commands): `git add <design-doc>` then `git commit -m "docs: mark design doc as complete"`
3. Shut down all teammates, then clean up the team.

**Cleanup notes**: Shut down all teammates before cleaning up the team. Check `tmux ls` for orphans.

$ARGUMENTS
