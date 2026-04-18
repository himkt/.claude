---
name: research-presentation
description: Create a Slidev presentation and reading transcript from an existing research report folder. Reads report.md and researcher files for context, creates slides using /my-slidev skill and a reading transcript. Takes folder path as argument (e.g., topic-name). Do NOT use for research — use /research-report for that.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Research Presentation

Create a Slidev presentation and reading transcript from an existing research report folder. The Director spawns Presentation, Transcript, and per-batch Visual Reviewer members, reviews their output, and iterates until quality is met.

| Role | Identity | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Create CAFleet session, spawn all members via `cafleet member create`, review all deliverables, demand revisions, run Slidev server lifecycle and `agent-browser close --all` safety net | Create slides/transcript, conduct research, modify report, run agent-browser browser-operation commands (except close --all) | [roles/director.md](roles/director.md) |
| **Presentation** | Member agent (claude) | Create Slidev presentation from report using `/my-slidev` | Invent data, modify report, conduct research | [roles/presentation.md](roles/presentation.md) |
| **Transcript** | Member agent (claude) | Create reading transcript with 1:1 slide correspondence | Invent data, modify report, conduct research | [roles/transcript.md](roles/transcript.md) |
| **Visual Reviewer** | Member agent (claude) — one per batch | Capture screenshots/snapshots of all slides using the agent-browser CLI (`bun run agent-browser`) with a per-batch named session (`--session vr-batch-{start}`), identify visual issues including aesthetic quality, report findings to Director | Edit slide.md, modify report, fix issues directly | [roles/visual-reviewer.md](roles/visual-reviewer.md) |

## Prerequisites

The Director MUST be running inside a tmux session (required by `cafleet member create`). If `TMUX` is not set, abort with an explanatory message to the user before spawning anyone.

## CAFleet Primitives

| Purpose | CAFleet command |
|---|---|
| Create session + root Director placement | `cafleet session create --label "presentation-{topic-slug}"` — bootstraps the session + root Director + placement + Administrator in one transaction |
| Spawn a member agent | `cafleet --session-id <session-id> member create --agent-id <director-agent-id> --name "..." --description "..." -- "<prompt>"` |
| Director sends a message to a member | `cafleet --session-id <session-id> send --agent-id <director-agent-id> --to <member-agent-id> --text "..."` |
| Member sends a message to the Director | `cafleet --session-id <session-id> send --agent-id <my-agent-id> --to <director-agent-id> --text "..."` |
| Monitor the team | `Skill(cafleet-monitoring)` `/loop` |
| Shut down a member / tear down the team | `cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <member-agent-id>` per member, then `cafleet session delete <session-id>` |
| Auto message delivery | Push notification injects `cafleet --session-id <session-id> poll --agent-id <recipient-agent-id>` into the member's tmux pane |

## Director Process

### Step 0: Validate Input (Director)

1. If `$ARGUMENTS` is absent → error: "Usage: `/research-presentation {folder-name}`. Specify the folder containing report.md."
2. Load `Skill(base-dir)` and follow its procedure with `$ARGUMENTS` as the argument.
   - If skipped (absolute path): set `${FOLDER} = $ARGUMENTS`.
   - If base resolved: set `${FOLDER} = ${BASE}/researches/$ARGUMENTS`. Resolve to absolute path.
3. Check that `${FOLDER}/report.md` exists. If not, error: "No report.md found in `${FOLDER}`. Run `/research-report` first to generate a report."
4. Pass `${FOLDER}` as the resolved absolute path to all members in spawn prompts.

### Step 1: Start Progress Monitor (Director — MANDATORY)

Load `Skill(cafleet-monitoring)` and follow its Monitoring Mandate. Set up a `/loop` monitor BEFORE spawning any member. The loop checks `${FOLDER}` for expected files (`slide.md`, `transcript.md`) and nudges stalled members via `cafleet send` and `cafleet member capture`. Keep it running until Step 6.

### Step 2: Create Session & Spawn Presentation + Transcript (Director)

#### 2a. Create the CAFleet session and capture the root Director's `agent_id`

```bash
cafleet session create --label "presentation-{topic-slug}" --json
```

Capture `session_id` and `director.agent_id` from the JSON response. Substitute them for `<session-id>` and `<director-agent-id>` in every subsequent command. **Do not store them in shell variables** — `permissions.allow` matches command strings literally, so every command must carry the literal UUIDs.

#### 2b. Read role definitions

Read the role files that will be embedded verbatim in spawn prompts:

- `~/.claude/skills/research-presentation/roles/presentation.md`
- `~/.claude/skills/research-presentation/roles/transcript.md`
- `~/.claude/skills/research-presentation/roles/visual-reviewer.md`

#### 2c. Spawn Presentation + Transcript members in parallel

Both work from `report.md` independently. After the slide deck is finalized (Step 3), the Director sends the final slide structure to the Transcript member for realignment.

**Presentation member spawn prompt:**

```
You are the Presentation Specialist in a research presentation team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-presentation/roles/presentation.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(cafleet) — for communication with the Director
- Skill(my-slidev) — for Slidev authoring layouts and rules
- Skill(create-figure) — if the report includes data that would render better as a chart
- Also Read ~/.claude/agents/slide-creator.md for Slidev authoring methodology

SESSION ID: <session-id>
DIRECTOR AGENT ID: <director-agent-id>
YOUR AGENT ID: <my-agent-id>
TASK: Create a Slidev presentation from the approved research report.
REPORT:           [INSERT {folder}/report.md]
RESEARCHER FILES: [INSERT {folder}/[0-9][0-9]-research-*.md]
LANGUAGE:         [INSERT language detected from report.md]
FIGURE BASE:      [INSERT {folder}]    (substitute literally for ${FIGURE_BASE}/${BASE} in create-figure)
OUTPUT:           [INSERT {folder}/slide.md]

COMMUNICATION PROTOCOL:
- Report to Director: cafleet --session-id <session-id> send --agent-id <my-agent-id> --to <director-agent-id> --text "your report"
- When you see cafleet poll output with a message from the Director, act on those instructions and ack the task.

When complete, send the file path to the Director.
```

Spawn with:

```bash
cafleet --session-id <session-id> --json member create --agent-id <director-agent-id> \
  --name "Presentation" \
  --description "Creates Slidev presentation from report" \
  -- "<Presentation spawn prompt>"
```

Parse `agent_id` and substitute for `<presentation-agent-id>`.

**Transcript member spawn prompt:**

```
You are the Transcript Specialist in a research presentation team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-presentation/roles/transcript.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(cafleet) — for communication with the Director

SESSION ID: <session-id>
DIRECTOR AGENT ID: <director-agent-id>
YOUR AGENT ID: <my-agent-id>
TASK: Create a reading transcript from the approved research report.
REPORT:   [INSERT {folder}/report.md]
LANGUAGE: [INSERT language detected from report.md]
OUTPUT:   [INSERT {folder}/transcript.md]

COMMUNICATION PROTOCOL:
- Report to Director: cafleet --session-id <session-id> send --agent-id <my-agent-id> --to <director-agent-id> --text "your report"
- When you see cafleet poll output with a message from the Director, act on those instructions and ack the task.

When complete, send the file path to the Director.
```

Spawn with:

```bash
cafleet --session-id <session-id> --json member create --agent-id <director-agent-id> \
  --name "Transcript" \
  --description "Creates reading transcript from report" \
  -- "<Transcript spawn prompt>"
```

Parse `agent_id` and substitute for `<transcript-agent-id>`.

### Step 3: Content Review & Revision Loop (Director)

Read the output files (`${FOLDER}/slide.md`, `${FOLDER}/transcript.md`) and review using the tag criteria in [roles/director.md](roles/director.md). Send tagged feedback via `cafleet send`; members revise and resubmit. See [roles/director.md](roles/director.md) for revision approach and iteration limits.

```bash
cafleet --session-id <session-id> send --agent-id <director-agent-id> \
  --to <presentation-agent-id> --text "[SLIDE STRUCTURE] ... / [VISUAL] ... / ..."
```

### Step 4: Visual Review & Fix (Director)

After the content revision loop completes, visually review the rendered presentation.

**Server Startup (once):**

**Working directory: project root** (the directory containing `node_modules/` and `skills/`). Do NOT cd to plugin source directories — they are source repos, not runnable installations.

1. From the project root, run `bun install --frozen-lockfile` to ensure dependencies
2. Start Slidev dev server (`run_in_background: true`):
   - **macOS**: `script -q /dev/null bun run slidev --open false {folder}/slide.md`
   - **Linux**: `script -qfc "bun run slidev --open false {folder}/slide.md" /dev/null`
3. Set `{server_url}` to the Slidev dev server URL (default: `http://localhost:3030`). Use this value when spawning Visual Reviewers.
4. Create the persistent screenshots directory: write `{folder}/screenshots/.keep` (empty file) using the Write tool. This is a one-time operation per `/research-presentation` invocation; do NOT delete or wipe it on subsequent batches. agent-browser does not auto-create parent directories when given an explicit `screenshot <path>`, so this step is required for VR's per-slide capture to succeed.
5. Director MUST NOT run `bun run agent-browser --session vr-batch-* open|snapshot|screenshot|wait|close` directly — agent-browser is exclusively for Visual Reviewers (the only exception is the `close --all` safety net in Step 6). The Director MAY run `console` and `errors` for diagnostics if needed (e.g., investigating a stuck VR), but should prefer letting the VR do it.

**Batched Review Loop** (batch_size=10, fresh Visual Reviewer per batch to avoid context overflow):

Run the loop serially: spawn one Visual Reviewer via `cafleet member create`, wait for its report via `cafleet poll`, run the fix-and-recheck sub-loop, shut it down with `cafleet member delete`, then advance to the next batch. Do not spawn multiple Visual Reviewers in parallel — fixes from one batch can affect later batches, and parallel agent-browser sessions race on the same Slidev dev server.

```
total_slides = count slides in slide.md
start = 1

while start <= total_slides:
    end = min(start + 9, total_slides)

    vr_round = 1                                # current VR round number; bumped on each re-check
    spawn Visual Reviewer (cafleet member create --name VR-batch-{start}) with slides [start..end], ROUND=vr_round
    # spawn prompt MUST include `RESEARCH FOLDER: {folder}` and `ROUND: 1` lines so the VR
    # can build screenshot/report paths

    while True:                                 # initial review (r1) + up to 2 re-checks (r2, r3)
        wait for report from VR for round {vr_round} via cafleet poll
        if no issues: break
        if vr_round >= 3: break                 # max 2 re-check rounds reached; remaining issues escalate to user in Step 5
        route issues to Presentation member via cafleet send → fix
        vr_round += 1
        send re-check request to VR via cafleet send with a `ROUND: {vr_round}` line
        # VR writes the next capture to `vr{start}-r{vr_round}-p{slide_number}.png` and
        # the next persisted report to `vr{start}-r{vr_round}.md`, preserving prior rounds

    send `bun run agent-browser --session vr-batch-{start} close` instruction to Visual Reviewer via cafleet send  # MUST close the current batch session before shutdown
    cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <vr-agent-id>
    start = end + 1
```

**Visual Reviewer spawn prompt** (per batch):

```
You are the Visual Reviewer in a research presentation team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-presentation/roles/visual-reviewer.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(cafleet) — for communication with the Director

SESSION ID: <session-id>
DIRECTOR AGENT ID: <director-agent-id>
YOUR AGENT ID: <my-agent-id>
TASK: Visually verify the rendered Slidev presentation.
SLIDE FILE:      [INSERT {folder}/slide.md]
RESEARCH FOLDER: [INSERT {folder}]
SERVER URL:      [INSERT {server_url}]
SESSION NAME:    [INSERT vr-batch-{start}]
CHECK SLIDES:    [INSERT {start} to {end}]
ROUND:           [INSERT {round}]

COMMUNICATION PROTOCOL:
- Report to Director: cafleet --session-id <session-id> send --agent-id <my-agent-id> --to <director-agent-id> --text "your report"
- When you see cafleet poll output with a message from the Director, act on those instructions and ack the task.

When complete, persist the report to {folder}/screenshots/vr{start}-r{round}.md and send it to the Director via cafleet send.
```

Spawn with:

```bash
cafleet --session-id <session-id> --json member create --agent-id <director-agent-id> \
  --name "VR-batch-{start}" \
  --description "Visual Reviewer for batch {start}-{end}" \
  -- "<Visual Reviewer spawn prompt>"
```

### Step 5: User Approval & Revision Loop (Director)

Present deliverables (slides, transcript, preview URL) and request approval via `AskUserQuestion`. Report any known visual issues.

If the user requests revisions:

1. Triage feedback — slides → Presentation member, transcript → Transcript member
2. Route feedback via `cafleet send` using tag-based format, members revise
3. If slides changed, spawn a fresh Visual Reviewer for affected slides only (same serial pattern as Step 4)
4. Re-present and request approval again

No round limit — loop until approved.

### Step 6: Finalize & Clean Up (Director)

**Only enter after user approves in Step 5.**

1. Cancel the `/loop` monitor (`CronDelete` on the cron ID captured when the loop was created).
2. If any Visual Reviewer is still running: send it the instruction `bun run agent-browser --session vr-batch-{start} close` via `cafleet send` BEFORE member delete.
3. Shut down each member:
   ```bash
   cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <vr-agent-id>
   cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <presentation-agent-id>
   cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <transcript-agent-id>
   ```
4. After all members exit, Director runs the safety net:
   ```bash
   bun run agent-browser close --all
   ```
5. Kill the Slidev dev server if still running (stop the background Bash task started at Step 4).
6. Tear down the session:
   ```bash
   cafleet session delete <session-id>
   # → Deleted session <session-id>. Deregistered N agents.
   ```

`session delete` soft-deletes the `sessions` row and physically deletes every associated `agent_placements` row while preserving all `tasks` rows for audit.

$ARGUMENTS
