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

### Step 1: Create Team & Spawn Agents (Director)

Create the team and spawn both agents in parallel:

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

**Visual Reviewer spawn prompt (spawned just-in-time at Step 4):**

```
You are a Visual Reviewer and a teammate in a research team.

Read your role definition at: skills/research-presentation/roles/visual-reviewer.md

YOUR TASK: Visually verify the rendered Slidev presentation using playwright-mcp browser tools.
SLIDE FILE: {folder}/slide.md
SCREENSHOT DIR: {folder}/screenshots/
SERVER URL: {server_url}

PROCESS:
1. Navigate to the provided SERVER URL to confirm connectivity
2. For each slide: navigate to {server_url}/{slide_number},
   take a screenshot (save to {folder}/screenshots/slide-{N}.png),
   take an accessibility snapshot, check for visual issues

VISUAL ISSUE CATEGORIES: [OVERFLOW], [BROKEN_LAYOUT], [MISSING_CONTENT], [OVERLAP], [EMPTY_SLIDE], [RENDER_ERROR], [TEXT_WRAPPING]

When complete, send your review report to the Director.
```

**Parallelism strategy:** Both agents start in parallel from the approved report. The Presentation Agent builds the slide deck; the Transcript Agent drafts a preliminary narration script based on the report's section structure. Because the slide deck may not be finalized when the Transcript Agent starts, the workflow has two phases:

1. **Initial phase (parallel):** Both agents work independently from the report. The Transcript Agent uses the report's structure as a provisional slide outline.
2. **Alignment phase (after Presentation review):** Once the Director has a finalized slide deck (after Step 2/3 review), the Director sends the finalized slide structure to the Transcript Agent. The Transcript Agent realigns its narration to match the actual slides — adjusting headings, ordering, and content to achieve exact 1:1 correspondence.

### Step 2: Review Slides & Transcript (Director)

Read the output files and review using the tag criteria in [roles/director.md](roles/director.md). See [roles/director.md](roles/director.md) for report modification policy.

### Step 3: Revision Loop (Director)

- Send tagged feedback to the Presentation and/or Transcript agents
- Agents revise and resubmit
- Re-review against the same criteria
- See [roles/director.md](roles/director.md) for revision approach and iteration limits

### Step 4: Visual Review & Fix (Director)

After the content revision loop completes and the Director is satisfied with slide content, perform a visual review of the rendered presentation.

**Constraint**: Playwright MCP supports only one browser session at a time. Visual Reviewers accumulate context quickly (snapshots per slide). To avoid context overflow, process slides in batches of up to 10, with a fresh Visual Reviewer per batch.

**Server Startup (once):**

1. Run `bun install` to ensure dependencies are available.
2. Start the Slidev dev server (run_in_background):
   - **macOS**: `script -q /dev/null bun run slidev --open false {folder}/slide.md`
   - **Linux**: `script -qfc "bun run slidev --open false {folder}/slide.md" /dev/null`
3. **Director MUST NOT use any `mcp__playwright__*` tools** — all Playwright usage is exclusively for Visual Reviewer teammates.

**Batched Review Loop:**

```
total_slides = count slides in slide.md
batch_size = 10
start = 1

while start <= total_slides:
    end = min(start + batch_size - 1, total_slides)

    # 1. Spawn a fresh Visual Reviewer for this batch
    spawn Visual Reviewer with slides [start..end]

    # 2. Inner fix loop (max 2 rounds per batch)
    for round in 1..2:
        wait for Visual Reviewer report

        if no issues:
            break

        # Route issues to Presentation Agent for fix
        send tagged feedback to Presentation Agent
        wait for Presentation Agent to fix

        # Re-check only affected slides
        send re-check request to Visual Reviewer

    # 3. Close browser and shutdown this Visual Reviewer
    #    MUST close browser BEFORE shutdown to release the Playwright session.
    #    Otherwise the next batch's Visual Reviewer will fail with
    #    "Browser is already in use" error.
    send "close browser with mcp__playwright__browser_close" to Visual Reviewer
    shutdown Visual Reviewer

    # 4. Move to next batch
    start = end + 1
```

**Visual Reviewer spawn prompt** (per batch):

```
You are a Visual Reviewer. Read: roles/visual-reviewer.md

CHECK SLIDES {start} TO {end} ONLY.
SERVER URL: http://localhost:3030

Report ONLY slides with issues. If all pass, say "ALL PASS".
```

**Why batched**: Each Visual Reviewer accumulates ~1MB+ of context per 10 slides (accessibility snapshots, screenshots). A single reviewer checking 40+ slides will hit context limits and stop responding. Fresh reviewers per batch avoid this.

### Step 5: Present Deliverables to User (Director)

After the Director approves all deliverables internally, present them to the user:

1. **File paths** — list deliverable files:
   - Slides: `{folder}/slide.md`
   - Transcript: `{folder}/transcript.md`
2. **Slide preview command**: `bun run slidev {folder}/slide.md`
3. **Request for feedback** — explicitly ask the user to review and provide feedback or approve

### Step 6: User Revision Loop (Director)

When the user provides feedback after reviewing the deliverables:

1. **Triage the feedback** — determine which agent(s) need to act:
   - Slides feedback → Presentation Agent
   - Transcript feedback → Transcript Agent
2. **Route feedback** to the relevant agent(s) using the same tag-based format
3. **Agents revise** and send updated deliverables back to you
4. **Visual re-review (conditional):** If the Presentation Agent modified slides, spawn a fresh Visual Reviewer to check only the changed slides (same pattern as Step 4 but scoped to affected slide numbers only).
5. **Re-review** the changes, then re-present to the user (return to Step 5)

This loop repeats until the user explicitly approves all deliverables.

### Step 7: Finalize & Clean Up (Director)

1. Confirm all final deliverables are saved
2. **Shutdown sequence:**
   1. If a Visual Reviewer is still running, send "close browser with mcp__playwright__browser_close" BEFORE shutdown
   2. Send shutdown requests to: Presentation Agent, Transcript Agent, Visual Reviewer
   3. Kill the Slidev dev server background process if still running
   4. Clean up the team

**Cleanup notes**: Shut down all teammates before cleaning up the team. Kill the Slidev dev server background task if still running. Check `tmux ls` for teammate orphans (`teammateMode: "tmux"` runs each teammate in a tmux session — this check is unrelated to the Slidev server).

$ARGUMENTS
