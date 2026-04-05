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
| **Visual Reviewer** | `general-purpose` | Capture screenshots/snapshots of all slides using playwright-mcp, identify visual issues including aesthetic quality, report findings to Director | Edit slide.md, modify report, fix issues directly | [roles/visual-reviewer.md](roles/visual-reviewer.md) |

## Architecture

```
User (or chained from /research-report)
 └── Director (main Claude — creates team, spawns agents, reviews deliverables)
       ├── Presentation Agent (general-purpose teammate — creates Slidev slides using /my-slidev)
       ├── Transcript Agent (general-purpose teammate — creates reading transcript)
       └── Visual Reviewer (general-purpose teammate — spawned just-in-time at Step 4 after content review)
```

## Validation Rules

| Condition | Behavior |
|-----------|----------|
| Folder path argument omitted | Error: "Usage: `/research-presentation {folder-name}`. Specify the folder containing report.md." |
| `report.md` not found in folder | Error: "No report.md found in `{folder}`. Run `/research-report` first to generate a report." |
| `report.md` exists | Proceed normally |

## Director Process

### Step 0: Validate Input (Director)

1. If `$ARGUMENTS` is absent → error: "Usage: `/research-presentation {folder-name}`. Specify the folder containing report.md."
2. Load `Skill(base-dir)` and follow its procedure with `$ARGUMENTS` as the argument.
   - If skipped (absolute path): set `${FOLDER} = $ARGUMENTS`.
   - If base resolved: set `${FOLDER} = ${BASE}/researches/$ARGUMENTS`. Resolve to absolute path.
3. Check that `${FOLDER}/report.md` exists. If not, error: "No report.md found in `${FOLDER}`. Run `/research-report` first to generate a report."
4. Pass `${FOLDER}` as the resolved absolute path to all teammates in spawn prompts.

### Step 1: Start Progress Monitor (Director — MANDATORY)

Load `Skill(agent-team-supervision)` and follow its Monitoring Mandate. Set up a `/loop` monitor BEFORE proceeding to any subsequent step. The loop checks `${FOLDER}` for expected files (slide.md, transcript.md) and nudges stalled teammates. Keep it running until Step 7.

### Step 2: Create Team & Spawn Agents (Director)

Create the team and spawn Presentation + Transcript agents in parallel. Both work from `report.md` independently. After the slide deck is finalized (Step 3), the Director sends the final slide structure to the Transcript Agent for realignment.

**Presentation Agent spawn prompt:**

```
You are a Presentation Specialist and a teammate in a research team.

Load the slidev skill using: Skill(slidev)
Load the my-slidev skill using: Skill(my-slidev)
Read your role definition at: skills/research-presentation/roles/presentation.md

YOUR TASK: Create a Slidev presentation based on the approved research report.
REPORT FILE: {folder}/report.md
RESEARCHER FILES: {folder}/[0-9][0-9]-research-*.md (for additional context)
LANGUAGE: {detected from report.md}

FIGURE CREATION: Actively use /create-figure to create data visualizations
(charts, graphs, plots) from report data. When the report contains numerical
data, trends, comparisons, or distributions, create figures rather than
showing data as text-only bullets. Choose the right representation for each
dataset — figures for visual patterns, tables for reference data and exact
values. Set FIGURE_BASE to {folder} before loading Skill(create-figure).
This makes figures go to {folder}/figures/output/. Embed with
![description](./figures/output/filename.png).

CITATION RULES: Carry [N] citations from the report into slides. Renumber
sequentially based on first slide appearance. Add References slide(s) at the
end listing only cited sources.

TIMING: Design for a 30–60 minute presentation (~1.5–2 min per content slide).

Save the presentation to: {folder}/slide.md

When complete, send the file path to the Director.
```

**Transcript Agent spawn prompt:**

```
You are a Transcript Specialist and a teammate in a research team.

Read your role definition at: skills/research-presentation/roles/transcript.md

YOUR TASK: Create a reading transcript based on the approved research report.
REPORT FILE: {folder}/report.md
LANGUAGE: {detected from report.md}

Start by drafting a preliminary narration based on the report's section structure.
The Director will send you the finalized slide structure once available for realignment.

Save the transcript to: {folder}/transcript.md

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
4. Director MUST NOT use any `mcp__playwright__*` tools — Playwright is exclusively for Visual Reviewers.

**Batched Review Loop** (batch_size=10, fresh Visual Reviewer per batch to avoid context overflow):

```
total_slides = count slides in slide.md
start = 1

while start <= total_slides:
    end = min(start + 9, total_slides)

    spawn Visual Reviewer with slides [start..end]

    for round in 1..2:                          # max 2 fix rounds per batch
        wait for report
        if no issues: break
        route issues to Presentation Agent → fix → re-check affected slides

    send "mcp__playwright__browser_close" to Visual Reviewer  # MUST close before shutdown
    shutdown Visual Reviewer
    start = end + 1
```

**Visual Reviewer spawn prompt** (per batch):

```
You are a Visual Reviewer and a teammate in a research team.

Read your role definition at: skills/research-presentation/roles/visual-reviewer.md

YOUR TASK: Visually verify the rendered Slidev presentation using playwright-mcp browser tools.
SLIDE FILE: {folder}/slide.md

CHECK SLIDES {start} TO {end} ONLY.
SERVER URL: {server_url}

PROCESS:
1. Navigate to SERVER URL to confirm connectivity
2. For each slide: navigate to {server_url}/{slide_number},
   take a screenshot and accessibility snapshot, check for visual issues.
   Screenshots are for in-session review only — do NOT persist them.

VISUAL ISSUE CATEGORIES: [OVERFLOW], [BROKEN_LAYOUT], [MISSING_CONTENT], [OVERLAP], [EMPTY_SLIDE], [RENDER_ERROR], [TEXT_WRAPPING]

Report ONLY slides with issues. If all pass, say "ALL PASS".
```

### Step 5: User Approval (Director)

Present deliverables (slides, transcript, preview URL) and request approval via `AskUserQuestion`. Report any known visual issues. If user requests revision, route feedback to agents, re-review, and re-present. No round limit — loops until approved.

### Step 6: User Revision Loop (Director)

1. Triage feedback — Slides → Presentation Agent, Transcript → Transcript Agent
2. Route feedback using tag-based format, agents revise
3. If slides changed, spawn fresh Visual Reviewer for affected slides only (same pattern as Step 4)
4. Return to Step 5

### Step 7: Finalize & Clean Up (Director)

**Only enter after user approves in Step 5.**

1. Cancel the `/loop` monitor (`CronDelete`)
2. If Visual Reviewer running: send `mcp__playwright__browser_close` BEFORE shutdown
3. Send shutdown requests to all teammates
4. Kill Slidev dev server if still running
5. Clean up the team

$ARGUMENTS
