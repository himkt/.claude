---
name: design-doc-execute
description: Implement features based on a design document with TDD cycle. Use when the user asks to implement or execute a design document. Takes document path as argument. Do NOT implement a design document by reading it and coding manually — always invoke this skill instead.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet
---

# Design Doc Execute

Implement features based on a design document using up to four roles in an in-process agent team: Director (orchestrator), Programmer (implements), Tester (writes tests), and Verifier (E2E/integration testing). The Director judges which teammates to spawn based on the nature of the implementation tasks. For each step, the Tester writes unit tests first, the Director reviews and approves them, then the Programmer implements code to pass the tests. The Director also reviews the Programmer's implementation for code quality and design doc compliance before committing. After all TDD steps, the Verifier performs E2E/integration verification (Phase D) if spawned. After user approval, the Director runs the full publication flow: Step 6 pushes the feature branch and opens a PR with `@copilot` requested, Step 7 runs a cron-driven Copilot review loop that routes inline comments to the still-live Programmer / Tester and exits when Copilot approves or has been quiescent for 5 ticks, and Step 8 finalizes, commits the completion marker, pushes it (when the branch is tracked on origin), and tears the team down.

| Role | Identity | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Create team, spawn teammates, validate doc, assign steps, review tests against design doc, review implementation code for quality and compliance, commit after each phase, escalation arbitration, orchestrate TDD cycle | Write code, write tests | [roles/director.md](roles/director.md) |
| **Programmer** | `design-doc-executor` teammate | Implement code to pass tests, run tests, report results via `SendMessage`, escalate test defects to Director, update design doc checkboxes and Progress counter | Write or modify tests, commit code, communicate with user directly | [roles/programmer.md](roles/programmer.md) |
| **Tester** | `design-doc-tester` teammate | Read design doc, write unit tests per step, fix tests based on Director feedback, report to Director via `SendMessage` | Write implementation code, commit code, communicate with user directly | [roles/tester.md](roles/tester.md) |
| **Verifier** | `design-doc-verifier` teammate (optional) | E2E/integration testing, tool discovery, evidence collection (screenshots, logs, output), failure reporting with suggested fixes | Write code, write tests, commit, communicate with user directly | [roles/verifier.md](roles/verifier.md) |

## Additional resources

- For the document template, see: [../design-doc/template.md](../design-doc/template.md)
- For section guidelines and quality standards, see: [../design-doc/guidelines.md](../design-doc/guidelines.md)

## Architecture

The Director creates an in-process team with `TeamCreate` and spawns each needed teammate with `Agent(team_name=..., name=...)`. All coordination goes through `SendMessage` (auto-delivered) and the shared task list.

```
User
 +-- Director (main Claude — TeamCreate, Agent spawn, SendMessage orchestration)
      +-- Programmer (teammate: design-doc-executor — implements code to pass tests)
      +-- Tester (teammate: design-doc-tester — writes unit tests per step)
      +-- Verifier (teammate: design-doc-verifier, optional — E2E/integration testing)
```

- **Director ↔ User**: `AskUserQuestion` (clarification relay, approval interaction, feedback collection)
- **Director ↔ Programmer**: `SendMessage` (step assignments, test results, code review feedback, escalation)
- **Director ↔ Tester**: `SendMessage` (step assignments, test review feedback, test defect reports)
- **Director ↔ Verifier**: `SendMessage` (verification assignments, results, failure routing)
- **Director**: git operations (commit after each phase — tests and implementation separately)

Teammates cannot talk to the user directly — the Director always relays.

## Prerequisites

- `gh` must be authenticated for Steps 6 + 7. Lack of auth is NOT fatal — the Director checks `gh auth status` at Step 6a and falls back to Step 8 local-finalize, skipping the PR and Copilot review loop entirely. All other prerequisites (approved design doc, feature branch) remain unchanged.

## Process

### Step 1: Resolve Design Document Path (Director)

Before validation, resolve `$ARGUMENTS` into a concrete `design-doc.md` path.

#### Phase 1: Base Directory Resolution

Load `Skill(base-dir)` and follow its procedure with `$ARGUMENTS` as the argument.
- If skipped (absolute path): set `${RESOLVED_ARGS} = $ARGUMENTS`.
- If base resolved: set `${RESOLVED_ARGS} = ${BASE}/design-docs/$ARGUMENTS`. Resolve to absolute path.

#### Phase 2: Three-Tier Detection

Using `${RESOLVED_ARGS}`, apply a three-tier detection strategy, evaluated in order:

| Tier | Condition | Action |
|:--|:--|:--|
| 1 — Direct file path | `${RESOLVED_ARGS}` ends with `design-doc.md` | Use as-is |
| 2 — Slug directory | `${RESOLVED_ARGS}` is a directory that contains `design-doc.md` directly | Append `/design-doc.md` |
| 3 — Base directory | `${RESOLVED_ARGS}` is a directory containing `**/design-doc.md` (one level deep) | Enter discovery flow |

Tier evaluation is sequential and short-circuits.

#### Discovery Flow (Tier 3)

When the base directory tier matches:

1. **Discover**: Use Glob to find all `**/design-doc.md` files under the base directory, then filter results to keep only those exactly one level deep (i.e., `<base>/<slug>/design-doc.md`). Discard any deeper matches.
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

When `${RESOLVED_ARGS}` does not match any of the three tiers (not a file path ending in `design-doc.md`, not a directory containing `design-doc.md`, and no `**/design-doc.md` found underneath), display:

```
Invalid argument: `${RESOLVED_ARGS}`
Expected one of:
  - Path to a design-doc.md file (e.g., my-feature/design-doc.md)
  - Slug directory containing design-doc.md (e.g., my-feature/)
  - No argument (discovers all design docs in ${BASE}/design-docs/)
```

Then abort.

After resolution, the resolved path is used as the design document path for all subsequent steps.

### Step 2: Validate Design Document & Create Branch (Director)

Before creating the team:

1. Read the design document completely.
2. Check for `COMMENT(` markers using Grep. If found, resolve them directly: apply the requested changes and remove the markers. Verify with Grep that no `COMMENT(` markers remain before proceeding.
3. Check for `FIXME(claude)` markers in the codebase using Grep. If found, note them for the Programmer to resolve first.
4. Determine the step order and total number of steps.
5. **Create a feature branch if on the default branch.** Get the default branch with `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` and the current branch with `git branch --show-current`. If they match, use `AskUserQuestion` to propose the branch name `feat/<design-doc-slug>` and ask the user to approve before creating it. The user will create the branch themselves or approve the proposed name. If already on a non-default branch, skip this step.

### Step 3: Create Team & Spawn Teammates (Director)

Load `Skill(agent-team-supervision)` and `Skill(agent-team-monitoring)` and follow their protocols.

#### 3a. Create the team

```
TeamCreate(team_name="execute-<slug>", description="Design doc execution: <slug>")
```

#### 3b. Analyze implementation tasks to decide team composition

Based on the design document steps (see [roles/director.md](roles/director.md) for the full decision matrix):

| Task nature | Team composition |
|---|---|
| Code implementation | Programmer + Tester |
| Config/documentation only | Programmer only |
| E2E verification needed (user-visible changes, CLI/UI/API) | + Verifier |

#### 3c. Start the monitoring `/loop`

BEFORE spawning any teammate, follow `Skill(agent-team-monitoring)`'s protocol and start a `/loop` monitor at a 1–3 minute interval (recommended: 1 minute). This is the **team-health loop** — it stays active through Steps 3–5 and, when Step 6 runs, is swapped (create-before-delete order in Step 7a) for the augmented team-health + PR-review loop. Whichever loop is active gets `CronDelete`d in Step 8's cleanup.

#### 3d. Read role definitions

Read the role files that will be embedded verbatim in spawn prompts:

- `~/.claude/skills/design-doc-execute/roles/programmer.md`
- `~/.claude/skills/design-doc-execute/roles/tester.md` (if Tester needed)
- `~/.claude/skills/design-doc-execute/roles/verifier.md` (if Verifier needed)

#### 3e. Spawn the Programmer

**Programmer spawn prompt:**

```
You are the Programmer in a design document execution team.

<ROLE DEFINITION>
[Content of roles/programmer.md injected here verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(design-doc) — for template and guidelines

DESIGN DOCUMENT: [INSERT DESIGN DOC PATH]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- You do NOT talk to the user directly. The Director relays.
- Messages from the Director arrive automatically — you do not poll.

IMPORTANT: Do NOT commit code yourself. The Director handles all git operations.
IMPORTANT: If blocked, SendMessage the Director immediately instead of assuming.
IMPORTANT: Read and follow rules/bash-command.md for all Bash commands.

Start by reading the design document. Then wait for the Director to assign your first step.
```

Spawn with:

```
Agent(
  subagent_type="design-doc-executor",
  team_name="execute-<slug>",
  name="programmer",
  prompt="<Programmer spawn prompt>"
)
```

#### 3f. Spawn the Tester (if needed)

**Tester spawn prompt:**

```
You are the Tester in a design document execution team.

<ROLE DEFINITION>
[Content of roles/tester.md injected here verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(design-doc) — for template and guidelines

DESIGN DOCUMENT: [INSERT DESIGN DOC PATH]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- You do NOT talk to the user directly. The Director relays.
- Messages from the Director arrive automatically — you do not poll.

IMPORTANT: Do NOT commit code yourself. The Director handles all git operations.
IMPORTANT: Do NOT write implementation code — only test code.
IMPORTANT: If blocked, SendMessage the Director immediately instead of assuming.
IMPORTANT: Read and follow rules/bash-command.md for all Bash commands.

Start by reading the design document. Then wait for the Director to assign your first step.
```

Spawn with:

```
Agent(
  subagent_type="design-doc-tester",
  team_name="execute-<slug>",
  name="tester",
  prompt="<Tester spawn prompt>"
)
```

#### 3g. Spawn the Verifier (if needed)

**Verifier spawn prompt:**

```
You are the Verifier in a design document execution team.

<ROLE DEFINITION>
[Content of roles/verifier.md injected here verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(design-doc) — for template and guidelines

DESIGN DOCUMENT: [INSERT DESIGN DOC PATH]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- You do NOT talk to the user directly. The Director relays.
- Messages from the Director arrive automatically — you do not poll.

IMPORTANT: Do NOT commit code or modify implementation/test files.
IMPORTANT: If blocked, SendMessage the Director immediately instead of assuming.
IMPORTANT: Read and follow rules/bash-command.md for all Bash commands.

Start by reading the design document and discovering available tools.
Then wait for the Director to assign your first verification task.
```

Spawn with:

```
Agent(
  subagent_type="design-doc-verifier",
  team_name="execute-<slug>",
  name="verifier",
  prompt="<Verifier spawn prompt>"
)
```

See [roles/director.md](roles/director.md) for commit message conventions.

### Step 4: Execute Steps with Per-Step TDD Cycle (Director)

For each step in the design document:

#### Phase A: Test Writing

**Skip this phase entirely when the Tester was not spawned** (Programmer-only team composition for config/documentation-only steps). Proceed directly to Phase B and assign the step to the Programmer without a separate test-writing commit.

1. **Assign**: `SendMessage(to: "tester", summary: "assign step N", message: "Step N: <description>. Spec: <…>. Write unit tests and report file paths when done.")`.
2. **Wait** for the Tester's report message — it arrives automatically. If the test framework is ambiguous, the Tester will ask via `SendMessage`; relay to the user via `AskUserQuestion` and pass the answer back verbatim via `SendMessage`.
3. **Review tests** against the design doc. Send feedback via `SendMessage(to: "tester", ...)` if issues found. Repeat until satisfied.
4. **Commit tests** (separate commands, do NOT chain with `&&`):
   - `git add <test-files>`
   - `git commit -m "test: add tests for [feature description]"`

#### Phase B: Implementation

1. **Assign**: `SendMessage(to: "programmer", summary: "assign step N", message: "Step N: <description>. Tests at: <paths>. Implement to pass all tests, update design doc checkboxes and Progress counter, then report.")`.
2. **Wait** for the Programmer's report message — it arrives automatically. On suspected test defect, see [roles/director.md](roles/director.md) for the escalation protocol.
3. **Programmer updates design doc**: Checkboxes, timestamps, and Progress counter.

#### Phase C: Code Review (Director)

1. **Review**: Verify code matches design doc, quality is acceptable, no unnecessary changes.
2. **Feedback loop**: Send feedback via `SendMessage(to: "programmer", ...)` if issues found. Programmer fixes, re-runs tests, re-reports via `SendMessage`. Repeat until satisfied.
3. **Commit implementation** (separate commands, do NOT chain with `&&`):
   - `git add <files> <design-doc>`
   - `git commit -m "feat: [description of what was implemented]"`

Repeat from Phase A for the next step. Always include the design document in the implementation commit.

**Escalation Protocol (Test Defect):** If the Programmer reports a suspected test defect (implementation matches design doc but tests expect something different), the Director reads the design doc and test, then directs either the Tester to fix the test or the Programmer to adjust the implementation via `SendMessage`. 3-round limit before escalating to the user.

**On-Demand Verification**: Any teammate can request verification mid-task via `SendMessage` to the Director. The Director decides whether to route immediately or defer:

| Route immediately | Defer to Phase D |
|:--|:--|
| User-visible behavior change (UI, CLI output, API response) | Internal refactoring or data model change |
| Integration with external system | Adequately covered by unit tests |
| Behavior difficult to catch with unit tests alone | Verification requires setup from a later step |

### Phase D: Verification (Director) — conditional

**Skip this phase entirely if the Verifier was not spawned.** Proceed directly to Step 5 (User Approval).

If the Verifier was spawned, assign verification:

1. `SendMessage(to: "verifier", summary: "E2E verification", message: "Design document: <path>. Completed steps: <list>. Relevant files: <list>. Please perform E2E/integration verification and report results with evidence.")`.
2. Verifier discovers tools, executes E2E verification, captures evidence, reports results via `SendMessage`.
3. **Route failures**: Implementation bugs → `SendMessage(to: "programmer", ...)`, test gaps → `SendMessage(to: "tester", ...)`, spec issues → user.
4. Re-verify after fixes. Proceed to User Approval when all verifiable criteria pass.

### Step 5: User Approval (Director)

After all TDD steps complete but before finalization, present the implementation to the user for approval.

#### Success Criteria Verification

**Before presenting to the user**, verify the design document's Success Criteria section:

1. Read the `## Success Criteria` section from the design document.
2. For each criterion, verify it is satisfied by inspecting the implementation (grep, read files, run tests as needed).
3. Check off all satisfied criteria in the design document (`- [ ]` → `- [x]`).
4. If any criterion is NOT satisfied, resolve it before proceeding to user approval — route to Programmer or Tester as needed via `SendMessage`.

This step is **mandatory** and must not be skipped.

#### Change Presentation

1. **Git diff command** for the user to inspect (e.g., `git diff main...HEAD`).
2. **Step-by-step change summary** — concise prose of what changed per step (files modified, key behaviors).

#### Approval Interaction

Use `AskUserQuestion`:

| Option | Label | Description | Behavior |
|:--|:--|:--|:--|
| 1 | **Approve** | Proceed with push, PR creation, Copilot review loop, then finalize | Steps 6 → 7 → 8 |
| 2 | **Scan for COMMENT markers** | Add `COMMENT(name): feedback` markers to the changed source files, then select this option to process them | Scan and process markers (see Revision Loop below) |
| 3 | *(Other — built-in)* | *(Free text input, e.g. "approve but skip PR")* | Interpret user intent (see Revision Loop below). Intent judgment recognises an **approve-local** variant that skips Steps 6 + 7 and jumps straight to Step 8 (local finalize only, no push/PR). Abort intent triggers the Abort Flow. |

See [roles/director.md](roles/director.md) for user interaction rules (COMMENT handling, classification, intent judgment, abort detection).

#### Revision Loop (COMMENT Marker-Based Feedback)

When the user selects "Scan for COMMENT markers": scan changed files for `COMMENT(` markers. Classify by file location (see [roles/director.md](roles/director.md)) and route via `SendMessage`:
- Design-doc COMMENTs → Director resolves directly (no routing).
- Source-file COMMENTs → `SendMessage(to: "programmer", ...)`.
- Test-file COMMENTs → `SendMessage(to: "tester", ...)`.

After all COMMENTs are resolved and verified, re-present to user.

When the user selects "Other": interpret intent per [roles/director.md](roles/director.md) rules.

No round limit — the loop continues until the user approves or aborts.

#### Abort Flow

1. Update design document Status to "Aborted", add Changelog entry.
2. Commit (separate commands): `git add <design-doc>` then `git commit -m "docs: mark design doc as aborted"`
3. Follow Shutdown Protocol (Step 8: cancel whichever `/loop` is active — team-health if Step 6 was skipped, augmented if Step 7 started — then `SendMessage` shutdown requests to each teammate and `TeamDelete`).

### Step 6: Push & Create PR (Director)

After Step 5 Approve, the Director pushes the feature branch, opens a PR, and requests a Copilot review BEFORE marking the design doc complete. Every command is run as a separate Bash call — do NOT chain with `&&`.

#### 6a. Preconditions (checked in order; first failure aborts to Step 8 local-finalize)

| Check | Command | Failure action |
|:--|:--|:--|
| `gh` authenticated | `gh auth status` | Report `gh not authenticated; skipping PR creation` → Step 8 local-finalize |
| Not on default branch | `git branch --show-current` vs `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` | Report `on default branch; cannot open PR` → Step 8 local-finalize |
| Branch has commits beyond base | `git log <base>..HEAD --oneline` | Report `no commits to push` → Step 8 local-finalize |

#### 6b. Procedure

1. **Resolve owner/repo**: `gh repo view --json nameWithOwner --jq '.nameWithOwner'`. Capture the literal `<owner>/<repo>` string (e.g. `himkt/cafleet`) and substitute it into every `gh api repos/<owner>/<repo>/...` call below. Like the PR number, this is a literal string — NO shell variables.
2. **Initial push**: `git push -u origin <branch-name>`. If this fails (non-fast-forward, branch protection, etc.), report the exact stderr to the user and proceed to Step 8 local-finalize. NEVER force-push.
3. **Check for an existing PR on this branch**: `gh pr list --head <branch-name> --json number --jq '.[0].number // empty'`. If the result is non-empty, reuse that PR number. Otherwise, run `gh pr create --fill` and parse the printed URL's trailing number.
4. **Record PR number literally**: store the PR number (e.g. `42`) and substitute it into `<pr-number>` in every subsequent command. DO NOT use a shell variable — `permissions.allow` matches literal command strings.
5. **Request Copilot review**: `gh pr edit <pr-number> --add-reviewer @copilot`.
6. **Verify the review request**: `gh api repos/<owner>/<repo>/pulls/<pr-number>/requested_reviewers` should list Copilot. If Copilot is absent from the response AND no Copilot review already exists (`gh pr view <pr-number> --json reviews`), report `Copilot reviewer unavailable for this PR` and proceed to Step 8 local-finalize.
7. **Capture `last_push_ts`**: record the ISO 8601 timestamp of the push completion (the Director's wall-clock time captured immediately after step 2 returned, or `date -u +%Y-%m-%dT%H:%M:%SZ`). This initialises the in-context loop state described in the "PR Review Loop State" subsection below.

### Step 7: Copilot Review Loop (Director)

Once the PR exists and Copilot has been invited, the Director runs a cron-driven review loop. The team-health `/loop` is replaced by an **augmented** loop that keeps the team-health checks AND adds PR review polling.

#### PR Review Loop State

The Director holds three in-context variables across loop firings. They are NOT persisted to disk — the Director carries them in its own working memory.

| Variable | Meaning | Update rule |
|:--|:--|:--|
| `last_push_ts` | ISO 8601 timestamp of the most recent push to the PR branch | Reset on every `git push` from 6b-step 2 or 7d-step 3 |
| `ticks_since_last_new_review` | Number of consecutive loop ticks with 0 new Copilot items | Increment each tick; reset to 0 when new Copilot items arrive |
| `round` | Fix-round counter (push → Copilot review → fix cycle) | Increment after every push from 7d; reset only via 7e "Continue" |

#### 7a. Replace the monitoring `/loop` (create-before-delete)

On entry to Step 7:

1. **Start the augmented `/loop` first** with the template in "Augmented Loop Prompt" below. Record the new cron ID.
2. **Then `CronDelete` the existing team-health loop** (cron ID recorded in Step 3c).
3. The new loop keeps every team-health check AND adds PR review polling.

Order matters: create-before-delete eliminates any window where no monitor is running. A one-tick overlap (both loops firing for one minute) is harmless — the Director receives two nudge prompts and reconciles them trivially.

On exit from Step 7 (any exit condition), keep the augmented loop running — Step 8's shutdown is responsible for the final `CronDelete`.

#### 7b. Per-tick procedure

On each 1-minute wake-up, the Director runs — in order:

1. **Team health** (unchanged from `agent-team-monitoring`): deliverable scan → `TaskList` inspection → directed `SendMessage` nudge for stalled teammates.
2. **Fetch new PR reviews**: `gh pr view <pr-number> --json reviews` (GraphQL-shaped; fields are `author.login`, `state`, `submittedAt`, `body`) AND `gh api repos/<owner>/<repo>/pulls/<pr-number>/comments` (REST-shaped; fields are `user.login`, `body`, `path`, `line`, `created_at`).
3. **Filter Copilot-authored entries**: keep items where the login field (`author.login` for `gh pr view` reviews, `user.login` for `gh api` inline comments) matches the regex `^copilot` (case-insensitive). Copilot reviews currently post under a login that begins with `copilot` — the exact slug varies by account plan, so a prefix match is the safe filter.
4. **New-since-push filter**: keep items whose timestamp (`submittedAt` for reviews, `created_at` for inline comments) is strictly later than `last_push_ts`.
5. **Branch on the filter result**:

| Result | Action |
|:--|:--|
| The most recent Copilot-authored entry in `reviews` has `state == "APPROVED"` | Exit loop (success) → Step 8 |
| 0 new Copilot items AND `ticks_since_last_new_review >= 5` | Exit loop (quiescent) → Step 8 |
| 0 new Copilot items AND `ticks_since_last_new_review < 5` | Increment `ticks_since_last_new_review`, continue |
| ≥ 1 new Copilot items | Go to 7c |

**Why 5 ticks (not 3)**: Copilot's first review after a push can take 3–5 minutes. 3 ticks risks declaring quiescence while Copilot is still composing its response. 5 ticks (~5 minutes) gives the model comfortable headroom without dragging the session out indefinitely.

**Why not `reviewDecision`**: the PR-level `reviewDecision` only reflects required reviewers (typically CODEOWNERS). Copilot is usually not a CODEOWNER, so an approve from Copilot alone leaves `reviewDecision` null/REVIEW_REQUIRED. Reading the Copilot-specific entry in the `reviews` array is the reliable signal.

#### 7c. Classify and route

For each new inline comment, pick the owner by file-path pattern:

| Path pattern | Owner | Route |
|:--|:--|:--|
| Design doc (`design-docs/**/design-doc.md`) | Director | Director applies directly — no `SendMessage` route |
| Test file (e.g. `**/test_*.py`, `**/*_test.py`, `**/tests/**`) | Tester | `SendMessage(to: "tester", summary: "Copilot test review", message: "Copilot review: <file>:<line> — <comment body>. Please address.")` |
| Any other source file | Programmer | `SendMessage(to: "programmer", summary: "Copilot review", message: "Copilot review: <file>:<line> — <comment body>. Please address.")` |

For review-level comments (body text not attached to a specific line), route by Director judgment: spec-level → Director resolves directly; implementation-level → Programmer; test-level → Tester.

#### 7d. Fix, commit, push, re-request

1. Wait for each routed teammate to report completion via `SendMessage`. Teammates do NOT commit — the Director commits after each report.
2. Commit fixes per scope (each `git add` / `git commit` is its own Bash call, no `&&`):
   - Programmer fixes: `git commit -m "fix: address Copilot review - <short summary>"`
   - Tester fixes: `git commit -m "fix: address Copilot test review - <short summary>"`
   - Director doc fixes: `git commit -m "docs: address Copilot review - <short summary>"`
3. `git push` (no flags — the branch already tracks origin from Step 6).
4. Update `last_push_ts` to the post-push wall-clock timestamp, reset `ticks_since_last_new_review = 0`, and increment `round`.
5. Re-request Copilot review: `gh pr edit <pr-number> --add-reviewer @copilot`. Re-adding the same reviewer triggers a fresh Copilot pass.
6. Continue the loop.

#### 7e. Round limit

When `round >= 5`, break the auto-loop and escalate to the user via `AskUserQuestion`:

| Option | Behavior |
|:--|:--|
| 1. Continue | Reset `round = 0`, resume Step 7 |
| 2. Finalize now | Exit loop → Step 8 (accept remaining Copilot comments as-is) |
| 3. *(Other)* | Intent judgment; abort-intent → Abort Flow |

#### Augmented Loop Prompt

Use this as the `/loop` prompt for Step 7. Substitute the literal PR number before passing the prompt to `/loop` — no shell variables.

**Invocation form (mandatory):** `/loop 1m <prompt below>`. The `1m` argument is required — never omit it (that would enter dynamic/self-paced mode) and never substitute any other interval. See `Skill(agent-team-monitoring)` for interval guidance.

```
Skill(agent-team-monitoring) — tick for team "execute-<slug>", plus PR review polling (fixed interval: 1 minute — do NOT adjust).

Expected deliverables: <list>
Active teammates: programmer, tester (if spawned), verifier (if spawned)

TEAM HEALTH (per Skill(agent-team-monitoring)):
1. Deliverable scan: check expected files/paths.
2. TaskList inspection: look for in_progress tasks with stale updates.
3. Directed nudge: SendMessage the owner of any stalled task with a specific, actionable message.
4. Escalate to user after 2 consecutive stalled ticks on the same task.

PR REVIEW:
5. Run `gh pr view <pr-number> --json reviews` (GraphQL shape: `author.login`, `state`, `submittedAt`, `body`).
6. Run `gh api repos/<owner>/<repo>/pulls/<pr-number>/comments` (REST shape: `user.login`, `body`, `path`, `line`, `created_at`).
7. Filter to entries where the appropriate login field starts with `copilot` (case-insensitive) and the timestamp is strictly later than `<last-push-timestamp>`.
8. If the most recent Copilot-authored entry in `reviews` has `state == "APPROVED"`: signal Step 7 exit (success).
9. If filter returned 0 entries for 5 consecutive ticks: signal Step 7 exit (quiescent).
10. If filter returned ≥ 1 entries: classify by file path and route via SendMessage(to: "<teammate>", summary: "Copilot review", message: "Copilot review: <file>:<line> — <body>. Please address.").

ESCALATION:
11. If any teammate has been nudged 2 times with no progress, escalate to the user.
12. If `round >= 5`, escalate to the user with the Continue / Finalize-now / Other prompt.
```

#### Error Handling (Steps 6–7)

| Case | Detection | Behavior |
|:--|:--|:--|
| `gh auth status` fails | Step 6a precondition check | Skip Steps 6 + 7, go directly to Step 8 local-finalize |
| On default branch | Step 6a precondition check | Skip Steps 6 + 7, go directly to Step 8 local-finalize |
| No commits beyond base | Step 6a precondition check | Skip Steps 6 + 7, go directly to Step 8 local-finalize |
| `git push` rejected | stderr of `git push` | Report exact stderr to user, skip Step 7, go to Step 8 local-finalize. NEVER force-push. |
| `gh pr create` fails | stderr of `gh pr create` | Report, skip Step 7, go to Step 8 local-finalize |
| `@copilot` reviewer unavailable | `gh api .../requested_reviewers` shows no Copilot AND no prior Copilot review | Report `Copilot reviewer unavailable for this PR`; skip Step 7; go to Step 8 |
| Fix-push fails mid-loop (`round > 0`) | stderr of `git push` | Escalate to user (AskUserQuestion: retry / finalize now / abort) |
| Round limit reached (`round >= 5`) | Counter check in loop | AskUserQuestion — see 7e above |
| User selects "Other" in Step 5 with abort-intent text | Existing LLM intent judgment | Abort Flow (unchanged — no push) |
| User selects "Other" in Step 5 with approve-local intent | Existing LLM intent judgment, extended | Skip Steps 6 + 7; go to Step 8 local-finalize |

#### User Interjection During Step 7

`/loop` firings keep arriving while the user is speaking to the Director. The Director obeys the project's "Stop means stop" rule: when the user signals halt (explicit "stop", "wait", profanity / frustration, repeated rejection of tool calls), the Director:

1. Stops dispatching new `SendMessage` / `git commit` / `git push` / `gh` actions immediately.
2. Acknowledges the user briefly and waits for explicit instructions.
3. Treats subsequent `/loop` firings as notification-only — runs the PR review poll for situational awareness but does NOT route comments, commit, or push until the user re-engages with a specific instruction.
4. Does NOT silently tear the team down — the state stays paused so the user can resume or explicitly abort.

If the user explicitly aborts, follow the Abort Flow (update doc Status → "Aborted", commit, run Shutdown Protocol). Step 7's cleanup is identical to Step 8's cleanup — `CronDelete` the augmented loop, `SendMessage` shutdown to each teammate, `TeamDelete`.

### Step 8: Finalize & Clean Up (Director)

Runs after Step 7 exits, or directly after Step 5 when Step 6 was skipped (gh not authenticated / default branch / no commits / approve-local intent).

1. Update design document Status to "Complete" and add a final Changelog entry.
2. `git add <design-doc>` (separate Bash call).
3. `git commit -m "docs: mark design doc as complete"` (separate Bash call).
4. **Push decision** (separate Bash call): run `git rev-parse --abbrev-ref <branch-name>@{upstream}`.
   - Exit code 0 (branch is tracked on origin): `git push`. This covers both the "Step 6 fully succeeded" path and the "Step 6 partial-fail (push OK, PR create failed)" path, so the final docs commit is never orphaned locally when the branch is already on origin.
   - Non-zero exit (Step 6 was skipped before the `git push -u`): skip the push. The docs commit stays local.
   - The Director does NOT re-request Copilot review on this final docs commit — docs status changes are not worth another review round.
5. `CronDelete` the currently active `/loop` monitor — whichever cron ID is recorded: team-health (from Step 3c) if Step 6 was skipped, augmented (from Step 7) otherwise.
6. Shut down each spawned teammate:
   ```
   SendMessage(to: "programmer", message: {"type": "shutdown_request"})
   SendMessage(to: "tester", message: {"type": "shutdown_request"})        # if spawned
   SendMessage(to: "verifier", message: {"type": "shutdown_request"})      # if spawned
   ```
7. After all teammates have shut down, call `TeamDelete` to remove the team and task directories.
8. **Report to the user**: include the PR URL (if Step 6 created one), the review-round summary (rounds used, exit reason: approved / quiescent / round-limit / skipped), and any skipped-step reasons.

$ARGUMENTS
