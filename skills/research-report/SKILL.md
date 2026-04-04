---
name: research-report
description: Create a comprehensive research report with folder-based output using agent teams. Researchers write findings to individual files, Manager compiles report.md, Director reviews. Output goes to researches/{topic-slug}/. After report approval, offers to chain into /research-presentation for slides and transcript. Teammates must always load skills using the Skill tool, not by reading skill files directly. Requires CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS enabled. Do NOT do a quick web search and summarize — invoke this skill for thorough, multi-source research.
allowed-tools: Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Agent
---

# Research Report (Agent Teams Edition)

Generate comprehensive research reports using a multi-layer agent hierarchy: Director → Manager → Researchers. The defining characteristic of this system is that every member of the team carries serious accountability for the quality of the final deliverable, and the team iterates relentlessly until the report meets the highest standard. After the report is approved, the Director offers to chain into `/research-presentation` for slides and transcript.

| Role | Agent | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Spawn all teammates, review all deliverables, demand revisions | Write the report, decompose topics, conduct research | [roles/director.md](roles/director.md) |
| **Manager** | `general-purpose` | Light web search for topic decomposition, request researcher spawning, coordinate researchers, compile report, revise | Conduct deep investigation — all substantive research MUST be delegated to Researchers | [roles/manager.md](roles/manager.md) |
| **Scout** | `web-researcher` | Landscape mapping — broad discovery to expand knowledge before decomposition | Collect facts for the report, write report sections | [roles/scout.md](roles/scout.md) |
| **Researcher** | `web-researcher` | Search exhaustively, collect facts with sources, filter misinformation, write findings to assigned file | Synthesize or write report sections | [roles/researcher.md](roles/researcher.md) |

## Additional resources

- For the report format specification, see [template.md](template.md)

## Architecture

Only the lead (Director) can spawn teammates ([no nested teams](https://code.claude.com/docs/en/agent-teams#limitations)). Therefore, the Director spawns both the Manager and all Researchers as teammates. The Manager coordinates Researchers via direct messaging but requests the Director to spawn new ones when needed.

```
User
 └─ Director (main Claude, the lead — creates team, spawns all teammates, reviews all deliverables)
      ├─ Manager (teammate — orchestrates research, compiles report)
      └─ Researcher 1..N (teammates — spawned by Director on Manager's request)
```

- **Director ↔ Manager**: team messaging (task instructions, review feedback, spawn requests)
- **Manager ↔ Researchers**: team messaging (assignments, findings, follow-up questions)
- **Manager → Director**: spawn requests when additional Researchers are needed

## Process

### Step 0: Base Directory Selection (Director)

Before creating the team, determine where output files will be saved.

1. Load `Skill(base-dir)` and follow its procedure. (The topic argument is not a path, so the absolute-path skip rule does not apply.)
2. Compute: `${OUTPUT_DIR} = ${BASE}/researches/{topic-slug}/`
3. Create the output directory.
4. Pass `${OUTPUT_DIR}` as the resolved absolute path to the Manager and all Researchers in their spawn prompts.

### Step 1: Create Team & Launch Manager (Director)

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
9. **Output folder path**: Pass `${OUTPUT_DIR}` (the resolved absolute path from Step 0) to the Manager. The Manager writes the compiled report to `${OUTPUT_DIR}/report.md`. Researchers write to `${OUTPUT_DIR}/NN-{subtopic}.md`.
10. User's language preference (if specified)
11. Mandate: "Your first draft will be reviewed critically. Aim for highest quality on first attempt."
### Step 2: Knowledge Bootstrapping — Scout Phase (Director)

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

**Transition**: Once the Manager signals that scouting is complete and sends a Researcher spawn request, the Director proceeds to Step 3 (Spawn Researchers).

### Step 3: Spawn Researchers (Director)

After the Manager decomposes the topic and sends a spawn request, the Director spawns each Researcher as a teammate.

**Researcher spawn prompt template:**

```
You are a Research Specialist and a teammate in a research team.

Read your role definition at: roles/researcher.md

CURRENT DATE: {today's date}
YOUR ASSIGNMENT: [specific sub-topic and what to investigate]
OUTPUT FILE: {resolved-path}/NN-{subtopic}.md

Write findings to the output file, then message the Manager when complete.
```

The Director repeats this step whenever the Manager requests additional Researchers (e.g., for coverage gaps, failed investigations, or revision-driven re-research).

### Step 4: Critical Review (Director)

When the Manager finishes and sends you the completed report (messages are delivered automatically via the team mailbox), read the report file and review it critically against the checklist in [roles/director.md](roles/director.md).

### Step 5: Revision Loop (Director ↔ Manager)

**This is where report quality is forged.** The first draft is raw material. The revision loop transforms it into a polished deliverable.

When issues are found, message the Manager teammate with specific, categorized, tagged feedback. See [roles/director.md](roles/director.md) for feedback tags and severity definitions.

### Step 6: Iterate Until Quality Is Met (Director)

Re-review per [roles/director.md](roles/director.md) quality criteria. Once approved, proceed to Step 7.

### Step 7: Present Deliverables to User (Director)

After the Director approves the report internally, present it to the user:

1. **Summary of findings** — key insights from the report (2-3 sentences)
2. **File paths** — list deliverable files:
   - Report: `${OUTPUT_DIR}/report.md`
   - Researcher files: `${OUTPUT_DIR}/01-*.md`, `02-*.md`, etc. (raw research data for reference)
3. **Limitations** — any caveats, known gaps, or areas where sources were limited
4. **Request for feedback** — explicitly ask the user to review and provide feedback or approve

### Step 8: User Revision Loop (Director)

When the user provides feedback after reviewing the report:

1. **Route feedback to the Manager** using the same tag-based format (may trigger re-research via Researchers)
2. **Manager revises** the report and sends the updated version back to you
3. **Re-review** the changes, then re-present to the user (return to Step 7)

This loop repeats until the user explicitly approves the report.

### Step 9: Offer Presentation Chaining (Director)

After the user approves the report, offer to create a presentation:

```
AskUserQuestion:
  Question: "Would you like to create a presentation (slides + reading transcript) from this report?"
    (Adapt the question text to match the user's language)
  Options:
    - "Yes, create presentation"
    - "No, report only"
```

- **If yes:** Proceed to Step 10 (shut down all research agents and clean up the team), then invoke `/research-presentation ${OUTPUT_DIR}` via the Skill tool. Since `${OUTPUT_DIR}` is an absolute path, `/research-presentation` skips its own base directory prompt. A new team is created by `/research-presentation` with its own lifecycle.
- **If no:** Proceed directly to Step 10.

### Step 10: Finalize & Clean Up (Director)

1. Confirm all final deliverables are saved to `${OUTPUT_DIR}/`
2. **Shutdown sequence:**
   1. Send shutdown requests to: all Researchers
   2. Send shutdown request to: Manager
   3. Clean up the team

**Cleanup notes**: Shut down all teammates before cleaning up the team. Check `tmux ls` for orphans.

**Quality standards**: Defined in [template.md](template.md). All team members must follow them.

$ARGUMENTS
