---
name: research-presentation
description: Create a Slidev presentation and reading transcript from an existing research report folder. Reads report.md and researcher files for context, creates slides using /my-slidev skill and a reading transcript. Takes folder path as argument (e.g., topic-name). Do NOT use for research — use /research-report for that.
allowed-tools: Read, Write, Edit, Glob, Grep, Agent
---

# Research Presentation

Create a Slidev presentation and reading transcript from an existing research report folder. The Director spawns Presentation and Transcript agents, reviews their output, and iterates until quality is met.

| Role | Agent (`subagent_type`) | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Spawn all teammates, review all deliverables, demand revisions | Create slides/transcript, conduct research, modify report | [roles/director.md](roles/director.md) |
| **Presentation** | `general-purpose` | Create Slidev presentation from report using /my-slidev | Invent data, modify report, conduct research | [roles/presentation.md](roles/presentation.md) |
| **Transcript** | `general-purpose` | Create reading transcript with 1:1 slide correspondence | Invent data, modify report, conduct research | [roles/transcript.md](roles/transcript.md) |
| **Visual Reviewer** | `general-purpose` | Capture screenshots/snapshots of all slides using the agent-browser CLI (`bun run agent-browser`) with a per-batch named session (`--session vr-batch-{start}`), identify visual issues including aesthetic quality, report findings to Director | Edit slide.md, modify report, fix issues directly | [roles/visual-reviewer.md](roles/visual-reviewer.md) |

## Director Process

### Step 0: Validate Input (Director)

1. If `$ARGUMENTS` is absent → error: "Usage: `/research-presentation {folder-name}`. Specify the folder containing report.md."
2. Load `Skill(base-dir)` and follow its procedure with `$ARGUMENTS` as the argument.
   - If skipped (absolute path): set `${FOLDER} = $ARGUMENTS`.
   - If base resolved: set `${FOLDER} = ${BASE}/researches/$ARGUMENTS`. Resolve to absolute path.
3. Check that `${FOLDER}/report.md` exists. If not, error: "No report.md found in `${FOLDER}`. Run `/research-report` first to generate a report."
4. Pass `${FOLDER}` as the resolved absolute path to all teammates in spawn prompts.

### Step 1: Start Progress Monitor (Director — MANDATORY)

Load `Skill(agent-team-supervision)` and follow its Monitoring Mandate. Set up a `/loop` monitor BEFORE proceeding to any subsequent step. The loop checks `${FOLDER}` for expected files (slide.md, transcript.md) and nudges stalled teammates. Keep it running until Step 6.

### Step 2: Create Team & Spawn Agents (Director)

**Team creation (mandatory `TeamCreate` tool call):**
1. `TeamCreate(name="presentation-{topic-slug}")` — creates the team
2. `Agent(..., team_name="presentation-{topic-slug}")` — spawns each teammate within the team

Spawn Presentation + Transcript agents in parallel. Both work from `report.md` independently. After the slide deck is finalized (Step 3), the Director sends the final slide structure to the Transcript Agent for realignment.

**Presentation Agent spawn prompt:**

```
Read your role definition: skills/research-presentation/roles/presentation.md

TASK: Create a Slidev presentation from the approved research report.
REPORT:         {folder}/report.md
RESEARCHER FILES: {folder}/[0-9][0-9]-research-*.md
LANGUAGE:       {detected from report.md}
FIGURE BASE:    {folder}    (substitute literally for ${FIGURE_BASE}/${BASE} in create-figure)
OUTPUT:         {folder}/slide.md

When complete, send the file path to the Director.
```

**Transcript Agent spawn prompt:**

```
Read your role definition: skills/research-presentation/roles/transcript.md

TASK: Create a reading transcript from the approved research report.
REPORT:   {folder}/report.md
LANGUAGE: {detected from report.md}
OUTPUT:   {folder}/transcript.md

When complete, send the file path to the Director.
```

### Step 3: Review & Revision Loop (Director)

Read the output files and review using the tag criteria in [roles/director.md](roles/director.md). Send tagged feedback; agents revise and resubmit. See [roles/director.md](roles/director.md) for revision approach and iteration limits.

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

Run the loop serially: spawn one Visual Reviewer, wait for its report, run the fix-and-recheck sub-loop, shut it down, then advance to the next batch. Do not spawn multiple Visual Reviewers in parallel — fixes from one batch can affect later batches, and parallel agent-browser sessions race on the same Slidev dev server.

```
total_slides = count slides in slide.md
start = 1

while start <= total_slides:
    end = min(start + 9, total_slides)

    vr_round = 1                                # current VR round number; bumped on each re-check
    spawn Visual Reviewer with slides [start..end], ROUND=vr_round
    # spawn prompt MUST include `RESEARCH FOLDER: {folder}` and `ROUND: 1` lines so the VR
    # can build screenshot/report paths

    while True:                                 # initial review (r1) + up to 2 re-checks (r2, r3)
        wait for report from VR for round {vr_round}
        if no issues: break
        if vr_round >= 3: break                 # max 2 re-check rounds reached; remaining issues escalate to user in Step 5
        route issues to Presentation Agent → fix
        vr_round += 1
        send re-check request to VR with a `ROUND: {vr_round}` line in the team message
        # VR writes the next capture to `vr{start}-r{vr_round}-p{slide_number}.png` and
        # the next persisted report to `vr{start}-r{vr_round}.md`, preserving prior rounds

    send `bun run agent-browser --session vr-batch-{start} close` instruction to Visual Reviewer  # MUST close the current batch session before shutdown
    shutdown Visual Reviewer
    start = end + 1
```

**Visual Reviewer spawn prompt** (per batch):

```
Read your role definition: skills/research-presentation/roles/visual-reviewer.md

TASK: Visually verify the rendered Slidev presentation.
SLIDE FILE:      {folder}/slide.md
RESEARCH FOLDER: {folder}
SERVER URL:      {server_url}
SESSION NAME:    vr-batch-{start}
CHECK SLIDES:    {start} to {end}
ROUND:           {round}

When complete, persist the report to {folder}/screenshots/vr{start}-r{round}.md and send it to the Director.
```

### Step 5: User Approval & Revision Loop (Director)

Present deliverables (slides, transcript, preview URL) and request approval via `AskUserQuestion`. Report any known visual issues.

If the user requests revisions:

1. Triage feedback — slides → Presentation Agent, transcript → Transcript Agent
2. Route feedback using tag-based format, agents revise
3. If slides changed, spawn a fresh Visual Reviewer for affected slides only (same serial pattern as Step 4)
4. Re-present and request approval again

No round limit — loop until approved.

### Step 6: Finalize & Clean Up (Director)

**Only enter after user approves in Step 5.**

1. Cancel the `/loop` monitor (`CronDelete`)
2. If Visual Reviewer running: instruct it to run `bun run agent-browser --session vr-batch-{start} close` BEFORE shutdown. After all teammates exit, Director runs `bun run agent-browser close --all` as a safety net.
3. Send shutdown requests to all teammates
4. Kill Slidev dev server if still running
5. Clean up the team

$ARGUMENTS
