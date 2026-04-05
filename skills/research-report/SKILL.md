---
name: research-report
description: Create a comprehensive research report with folder-based output using agent teams. Researchers write findings to individual files, Manager compiles report.md, Director reviews. Output goes to researches/{topic-slug}/. After report approval, offers to chain into /research-presentation for slides and transcript. Teammates must always load skills using the Skill tool, not by reading skill files directly. Requires CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS enabled. Do NOT do a quick web search and summarize — invoke this skill for thorough, multi-source research.
allowed-tools: Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Agent
---

# Research Report (Agent Teams Edition)

Generate comprehensive research reports using a multi-layer agent hierarchy: Director → Manager → Scouts/Researchers. The defining characteristic of this system is that every member of the team carries serious accountability for the quality of the final deliverable, and the team iterates relentlessly until the report meets the highest standard. After the report is approved, the Director offers to chain into `/research-presentation` for slides and transcript.

| Role | Agent | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Spawn all teammates, review all deliverables, demand revisions | Write the report, decompose topics, conduct research | [roles/director.md](roles/director.md) |
| **Manager** | `general-purpose` | Run orientation searches for landscape understanding and topic decomposition, request Scout/Researcher spawning, coordinate Scouts and Researchers, compile report, revise | Conduct deep investigation — all substantive research MUST be delegated to Researchers | [roles/manager.md](roles/manager.md) |
| **Scout** | `web-researcher` | Landscape mapping — broad discovery to expand knowledge before decomposition | Collect facts for the report, write report sections | [roles/scout.md](roles/scout.md) |
| **Researcher** | `web-researcher` | Search exhaustively, collect facts with sources, filter misinformation, write findings to assigned file | Synthesize or write report sections | [roles/researcher.md](roles/researcher.md) |

## Additional resources

- For the report format specification, see [template.md](template.md)

## Architecture

Only the lead (Director) can spawn teammates ([no nested teams](https://code.claude.com/docs/en/agent-teams#limitations)). Therefore, the Director spawns the Manager, all Scouts, and all Researchers as teammates. The Manager coordinates Scouts and Researchers via direct messaging but requests the Director to spawn new ones when needed.

```
User
 └─ Director (main Claude, the lead — creates team, spawns all teammates, reviews all deliverables)
      ├─ Manager (teammate — orchestrates research, compiles report)
      ├─ Scout 1..N (teammates — spawned by Director on Manager's request)
      └─ Researcher 1..N (teammates — spawned by Director on Manager's request)
```

- **Director ↔ Manager**: team messaging (task instructions, review feedback, spawn requests)
- **Manager ↔ Scouts**: team messaging (landscape requests, findings, follow-up)
- **Manager ↔ Researchers**: team messaging (assignments, findings, follow-up questions)
- **Manager → Director**: spawn requests when additional Scouts or Researchers are needed

## Process

### Step 0: Base Directory Selection (Director)

Before creating the team, determine where output files will be saved.

1. Load `Skill(base-dir)` and follow its procedure. (The topic argument is not a path, so the absolute-path skip rule does not apply.)
2. Compute: `${OUTPUT_DIR} = ${BASE}/researches/{topic-slug}/`
3. Create the output directory.
4. Pass `${OUTPUT_DIR}` as the resolved absolute path to the Manager and all Researchers in their spawn prompts.

### Step 1: Start Progress Monitor (Director — MANDATORY)

Load `Skill(agent-team-supervision)` and follow its Monitoring Mandate. Set up a `/loop` monitor BEFORE proceeding to any subsequent step. The loop must check `${OUTPUT_DIR}` for these expected deliverables:

- `report.md` — required final compiled report from the Manager
- `00-scout-*.md` — Scout landscape/discovery notes (one or more files may exist)
- `NN-research-*.md` — Researcher findings files for delegated sub-topics (`NN` is the assigned number; one or more files may exist)

Use these rules so readiness/stall decisions are deterministic:

- After Scouts/Researchers have been assigned, progress should be visible via creation of at least one `00-scout-*.md` or `NN-research-*.md` file.
- Do not consider the workflow ready for Step 5 until `report.md` exists.
- If no new matching files appear in `${OUTPUT_DIR}` for an extended interval, or expected intermediate files stop increasing while teammates are still assigned, nudge stalled teammates.
- Keep the monitor running until Step 8.

### Step 2: Create Team & Launch Manager (Director)

You (Claude, the lead agent) create an agent team and spawn a Manager teammate. You do NOT decompose topics yourself — that is the Manager's operational decision.

Create the team and spawn the Manager with a prompt covering:

1. The user's original request in full
2. **Today's date** (e.g., "Current date: 2026-02-20"). This anchors what "recent" means for all research.
3. Instruction to read `roles/manager.md` for role definition and `roles/scout.md` for Scout role definition
4. Instruction to tell Researchers to read `roles/researcher.md`
5. **Knowledge Bootstrapping (Scout Phase)**: Before decomposing the topic, the Manager may request Scout(s) from the Director for landscape mapping. To request Scouts, send the Director a message specifying: scope of landscape to map, search angles, and output file paths (`${OUTPUT_DIR}/00-scout-{topic}.md`). The Director spawns each Scout as a `web-researcher` teammate. The Manager reviews Scout findings, may request follow-up scouting or new Scouts, with a maximum of 3 Scout-Manager iterations. The Manager's own searches have no query limit — search as needed for orientation.
6. How to request Researchers: send the Director a message specifying sub-topics, scope, angles, and assigned file paths. Director spawns them as `web-researcher` agent teammates. Manager coordinates via messaging.
7. Handle researcher failures: re-split topics and request new Researchers from Director
8. Report format specification (copy template rules from template.md)
9. **Output folder path**: Pass `${OUTPUT_DIR}` (the resolved absolute path from Step 0) to the Manager. The Manager writes the compiled report to `${OUTPUT_DIR}/report.md`. Researchers write to `${OUTPUT_DIR}/NN-research-{subtopic}.md`.
10. User's language preference (if specified)
11. Mandate: "Your first draft will be reviewed critically. Aim for highest quality on first attempt."
### Step 3: Knowledge Bootstrapping — Scout Phase (Director)

After the Manager assesses the topic, the Manager may request Scout(s) from the Director for landscape mapping before topic decomposition.

**Scout spawn prompt template:**

```
You are a Scout Researcher and a teammate in a research team.

Read your role definition at: roles/scout.md

CURRENT DATE: {today's date}
YOUR ASSIGNMENT: [landscape scope and what areas to map]
OUTPUT FILE: {resolved-path}/00-scout-{topic}.md

Write findings to the output file, then message the Manager when complete.
```

**Scout-Manager loop:**

1. Manager assesses the topic and decides which aspects need landscape scouting
2. Manager sends Director a spawn request specifying Scout(s) — topic scope, search angles, output file paths (`00-scout-{topic}.md`)
3. Director spawns Scout(s) as `web-researcher` teammates
4. Scout(s) investigate and write findings to their output files, then message Manager
5. Manager reads Scout output files, identifies knowledge gaps or promising leads
6. **Loop**: Manager may send Scout(s) back for targeted follow-up, or request new Scout(s) from Director for uncovered areas
7. **Termination**: Manager judges that sufficient landscape knowledge has been gathered to decompose the topic effectively

**Safety cap**: Maximum 3 Scout-Manager iterations (request → investigate → review constitutes one iteration). After 3 iterations, the Manager must proceed to topic decomposition with the knowledge gathered so far.

**Transition**: Once the Manager signals that scouting is complete and sends a Researcher spawn request, the Director proceeds to Step 4 (Spawn Researchers).

### Step 4: Spawn Researchers (Director)

After the Manager decomposes the topic and sends a spawn request, the Director spawns each Researcher as a teammate.

**Researcher spawn prompt template:**

```
You are a Research Specialist and a teammate in a research team.

Read your role definition at: roles/researcher.md

CURRENT DATE: {today's date}
YOUR ASSIGNMENT: [specific sub-topic and what to investigate]
OUTPUT FILE: {resolved-path}/NN-research-{subtopic}.md

Write findings to the output file, then message the Manager when complete.
```

The Director repeats this step whenever the Manager requests additional Researchers (e.g., for coverage gaps, failed investigations, or revision-driven re-research).

### Step 5: Review & Revision Loop (Director ↔ Manager)

When the Manager delivers the compiled report, read it and review critically against the checklist in [roles/director.md](roles/director.md). Send tagged feedback to the Manager; Manager revises and resubmits. Repeat until quality is met (aim for 2-3 rounds max).

### Step 6: Present to User (Director)

Present the approved report to the user with: summary of findings (2-3 sentences), file paths (report, scout files, researcher files), limitations, and request for feedback. If the user provides feedback, route it to the Manager, re-review, and re-present. Repeat until the user approves.

### Step 7: Offer Presentation Chaining (Director)

After user approval, offer to create a presentation via `AskUserQuestion` (adapt to user's language). If yes, proceed to Step 8, then invoke `/research-presentation ${OUTPUT_DIR}`. If no, proceed directly to Step 8.

### Step 8: Finalize & Clean Up (Director)

1. Cancel the `/loop` monitor (`CronDelete`)
2. Send shutdown requests to all Researchers, then Manager
3. Clean up the team

**Cleanup notes**: Shut down all teammates before cleaning up the team. Check `tmux ls` for orphans.

$ARGUMENTS
