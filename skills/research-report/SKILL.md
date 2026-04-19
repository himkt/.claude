---
name: research-report
description: Create a comprehensive research report with folder-based output. Researchers write findings to individual files, the Manager compiles report.md, and the Director reviews. Output goes to researches/<topic-slug>/. After report approval, offers to chain into /research-presentation for slides and transcript. Teammates must always load skills using the Skill tool, not by reading skill files directly. Do NOT do a quick web search and summarize — invoke this skill for thorough, multi-source research.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
---

# Research Report

Generate comprehensive research reports using a multi-layer team: Director → Manager → Scouts/Researchers. Every member of the team carries serious accountability for the quality of the final deliverable, and the team iterates relentlessly until the report meets the highest standard. After the report is approved, the Director offers to chain into `/research-presentation` for slides and transcript.

| Role | Identity | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Create CAFleet session, spawn all teammates via `cafleet member create`, relay Manager requests, review all deliverables, present to user | Write the report, decompose topics, conduct research | [roles/director.md](roles/director.md) |
| **Manager** | Member agent (claude) | Run orientation searches for landscape understanding and topic decomposition, request Scout/Researcher spawning from the Director, aggregate Scout and Researcher findings, compile report, revise | Conduct deep investigation — all substantive research MUST be delegated to Researchers | [roles/manager.md](roles/manager.md) |
| **Scout** | Member agent (claude) | Landscape mapping — broad discovery to expand knowledge before decomposition | Collect facts for the report, write report sections | [roles/scout.md](roles/scout.md) |
| **Researcher** | Member agent (claude) | Search exhaustively, collect facts with sources, filter misinformation, write findings to assigned file | Synthesize or write report sections | [roles/researcher.md](roles/researcher.md) |

## Additional resources

- For the report format specification, see [template.md](template.md)

## Architecture

The Director registers a CAFleet session, spawns the Manager, and spawns every Scout and Researcher via `cafleet member create`. All coordination flows through the persistent CAFleet message queue — every message is auditable via the admin WebUI.

```
User
 └─ Director (main Claude — cafleet session create, cafleet member create, orchestrates cycle)
      ├─ Manager (member agent — compiles the report)
      ├─ Scout 1..N (member agents — spawned by Director on Manager's request)
      └─ Researcher 1..N (member agents — spawned by Director on Manager's request)
```

- **Director ↔ User**: `AskUserQuestion` (final report presentation, feedback collection)
- **Director ↔ Manager**: `cafleet send` (spawn requests, review feedback, shutdown)
- **Director ↔ Scouts / Researchers**: `cafleet send` (findings reports, revision requests)
- **Manager → Director**: spawn requests (`cafleet send`) for Scouts and Researchers
- Members receive messages via push notification: the broker injects `cafleet --session-id <session-id> poll --agent-id <recipient-agent-id>` into the member's pane whenever a `cafleet send` is persisted. `--session-id` is global (before the subcommand); `--agent-id` is per-subcommand (after the subcommand name).

## Prerequisites

The Director MUST be running inside a tmux session (required by `cafleet member create`). If `TMUX` is not set, abort with an explanatory message to the user before spawning anyone.

## CAFleet Primitives

| Purpose | CAFleet command |
|---|---|
| Create session + root Director placement | `cafleet session create --label "research-<topic-slug>"` — bootstraps the session + root Director + placement + Administrator in one transaction |
| Spawn a member agent | `cafleet --session-id <session-id> member create --agent-id <director-agent-id> --name "..." --description "..." -- "<prompt>"` |
| Director sends a message to a member | `cafleet --session-id <session-id> send --agent-id <director-agent-id> --to <member-agent-id> --text "..."` |
| Member sends a message to the Director | `cafleet --session-id <session-id> send --agent-id <my-agent-id> --to <director-agent-id> --text "..."` |
| Monitor the team | `Skill(cafleet-monitoring)` `/loop` |
| Shut down a member / tear down the team | `cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <member-agent-id>` per member, then `cafleet session delete <session-id>` |
| Auto message delivery | Push notification injects `cafleet --session-id <session-id> poll --agent-id <recipient-agent-id>` into the member's tmux pane |

## Process

### Step 0: Base Directory Selection (Director)

Before creating the session, determine where output files will be saved.

1. Load `Skill(base-dir)` and follow its procedure. (The topic argument is not a path, so the absolute-path skip rule does not apply.)
2. Compute: `${OUTPUT_DIR} = ${BASE}/researches/<topic-slug>/`
3. Create the output directory.
4. Pass `${OUTPUT_DIR}` as the resolved absolute path to the Manager and all Researchers in their spawn prompts.

### Step 1: Start Progress Monitor (Director — MANDATORY)

Load `Skill(cafleet-monitoring)` and follow its Monitoring Mandate. Set up a `/loop` monitor BEFORE spawning any member. The loop must check `${OUTPUT_DIR}` for these expected deliverables:

- `report.md` — required final compiled report from the Manager
- `00-scout-*.md` — Scout landscape/discovery notes (one or more files may exist)
- `NN-research-*.md` — Researcher findings files for delegated sub-topics (`NN` is the assigned number; one or more files may exist)

Use these rules so readiness/stall decisions are deterministic:

- After Scouts/Researchers have been spawned, progress should be visible via creation of at least one `00-scout-*.md` or `NN-research-*.md` file.
- Do not consider the workflow ready for Step 5 until `report.md` exists.
- If no new matching files appear in `${OUTPUT_DIR}` for an extended interval, or expected intermediate files stop increasing while members are still active, nudge stalled members via `cafleet send` and fall back to `cafleet member capture` per the 2-stage health check in `Skill(cafleet-monitoring)`.
- Keep the monitor running until Step 8.

### Step 2: Create Session & Spawn Manager (Director)

#### 2a. Create the CAFleet session and capture the root Director's `agent_id`

`cafleet session create` (which must be run inside a tmux session) atomically creates the session and registers a root Director bound to the current tmux pane. Use `--json` so both IDs are machine-parseable:

```bash
cafleet session create --label "research-<topic-slug>" --json
```

Capture `session_id` and `director.agent_id` from the JSON response. Substitute them for `<session-id>` and `<director-agent-id>` in every subsequent command. **Do not store them in shell variables** — `permissions.allow` matches command strings literally, so every command must carry the literal UUIDs.

#### 2b. Read role definitions

Read the role files that will be embedded verbatim in spawn prompts:

- `~/.claude/skills/research-report/roles/manager.md`
- `~/.claude/skills/research-report/roles/scout.md`
- `~/.claude/skills/research-report/roles/researcher.md`

#### 2c. Spawn the Manager

**Manager spawn prompt:**

When constructing the prompt, substitute the literal `<session-id>` and `<director-agent-id>` UUIDs for the placeholders. The new member's own `<my-agent-id>` will be baked in automatically by `cafleet member create`'s `str.format()` substitution. Any literal `{` / `}` in the prompt text must be doubled (`{{` / `}}`).

```
You are the Manager in a research report team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-report/roles/manager.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(cafleet) — for communication with the Director

SESSION ID: <session-id>
DIRECTOR AGENT ID: <director-agent-id>
YOUR AGENT ID: {agent_id}
CURRENT DATE: [INSERT today's date]
USER REQUEST: [INSERT user's original request in full]
OUTPUT DIRECTORY: [INSERT ${OUTPUT_DIR}]
LANGUAGE: [INSERT user's language preference if specified]

COMMUNICATION PROTOCOL:
- Report to Director: cafleet --session-id <session-id> send --agent-id {agent_id} --to <director-agent-id> --text "your report"
- When you see cafleet poll output with a message from the Director, act on those instructions and ack the task.

To request Scouts or Researchers, send the Director a spawn request specifying: role (Scout or Researcher), scope, search angles, and output file path. The Director will run cafleet member create and relay the new member's findings back to you.

Your first draft will be reviewed critically. Aim for highest quality on the first attempt.
```

Spawn with:

```bash
cafleet --session-id <session-id> --json member create --agent-id <director-agent-id> \
  --name "Manager" \
  --description "Compiles the research report" \
  -- "<Manager spawn prompt with embedded role content>"
```

Parse `agent_id` from the JSON response and substitute it for `<manager-agent-id>` in every subsequent command.

#### 2d. Verify the Manager is live

```bash
cafleet --session-id <session-id> member list --agent-id <director-agent-id>
```

The Manager must show `status: active` with a non-null `pane_id`.

### Step 3: Knowledge Bootstrapping — Scout Phase (Director, on Manager's request)

After assessing the topic, the Manager may send the Director one or more Scout spawn requests via `cafleet send`. For each request, the Director spawns a Scout.

**Scout spawn prompt:**

```
You are a Scout Researcher in a research team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-report/roles/scout.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(cafleet) — for communication with the Director
- Also Read ~/.claude/agents/web-researcher.md for the detailed research methodology
  (Discovery Phase, query formulation, synthesis, output format)

SESSION ID: <session-id>
DIRECTOR AGENT ID: <director-agent-id>
YOUR AGENT ID: {agent_id}
CURRENT DATE: [INSERT today's date]
YOUR ASSIGNMENT: [landscape scope and what areas to map]
OUTPUT FILE: [INSERT <resolved-path>/00-scout-<topic>.md]

COMMUNICATION PROTOCOL:
- Report to Director: cafleet --session-id <session-id> send --agent-id {agent_id} --to <director-agent-id> --text "your report"
- When you see cafleet poll output with a message from the Director, act on those instructions and ack the task.

Write findings to the output file, then send a completion report to the Director. The Director will relay your findings to the Manager.
```

Spawn with:

```bash
cafleet --session-id <session-id> --json member create --agent-id <director-agent-id> \
  --name "Scout-<topic>" \
  --description "Landscape scout for <topic>" \
  -- "<Scout spawn prompt>"
```

**Scout-Manager loop (relayed through Director):**

1. Manager sends Director a Scout spawn request (`cafleet send`)
2. Director spawns the Scout via `cafleet member create`
3. Scout investigates, writes findings to the output file, sends completion report to the Director
4. Director relays the Scout's output file path (and any summary text) to the Manager
5. Manager reads the Scout file and may send a follow-up request (either targeted re-scouting, a new Scout, or proceed to decomposition)

**Safety cap**: Maximum 3 Scout-Manager iterations (request → investigate → review = one iteration). After 3 iterations, the Manager must proceed to topic decomposition with the knowledge gathered so far.

### Step 4: Spawn Researchers (Director, on Manager's request)

After decomposing the topic, the Manager sends the Director one or more Researcher spawn requests via `cafleet send`. For each request, the Director spawns a Researcher.

**Researcher spawn prompt:**

```
You are a Research Specialist in a research team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-report/roles/researcher.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(cafleet) — for communication with the Director
- Also Read ~/.claude/agents/web-researcher.md for the detailed research methodology
  (Discovery Phase, query formulation, synthesis, output format)

SESSION ID: <session-id>
DIRECTOR AGENT ID: <director-agent-id>
YOUR AGENT ID: {agent_id}
CURRENT DATE: [INSERT today's date]
YOUR ASSIGNMENT: [specific sub-topic and what to investigate]
OUTPUT FILE: [INSERT <resolved-path>/NN-research-<subtopic>.md]

COMMUNICATION PROTOCOL:
- Report to Director: cafleet --session-id <session-id> send --agent-id {agent_id} --to <director-agent-id> --text "your report"
- When you see cafleet poll output with a message from the Director, act on those instructions and ack the task.

Write findings to the output file, then send a completion report to the Director. The Director will relay findings and any follow-up questions between you and the Manager.
```

Spawn with:

```bash
cafleet --session-id <session-id> --json member create --agent-id <director-agent-id> \
  --name "Researcher-<NN>" \
  --description "Researches <subtopic>" \
  -- "<Researcher spawn prompt>"
```

The Director repeats this step whenever the Manager requests additional Researchers (for coverage gaps, failed investigations, or revision-driven re-research).

### Step 5: Review & Revision Loop (Director ↔ Manager, via `cafleet send`)

When the Manager delivers the compiled report:

1. The Director reads `${OUTPUT_DIR}/report.md` and reviews it critically against the checklist in [roles/director.md](roles/director.md).
2. The Director sends tagged feedback to the Manager:
   ```bash
   cafleet --session-id <session-id> send --agent-id <director-agent-id> \
     --to <manager-agent-id> --text "[FACTUAL ERROR] ... / [GAP] ... / ..."
   ```
3. The Manager revises the report (spawning additional Researchers as needed) and sends a completion message back.
4. Repeat until the Director judges quality is sufficient. Aim for 2–3 rounds maximum.

### Step 6: Present to User (Director)

Present the approved report to the user with: summary of findings (2–3 sentences), file paths (report, scout files, researcher files), known limitations, and a request for feedback. If the user provides feedback, route it to the Manager via `cafleet send`, re-review, and re-present. Repeat until the user approves.

### Step 7: Offer Presentation Chaining (Director)

After user approval, offer to create a presentation via `AskUserQuestion` (adapt to user's language). If yes, proceed to Step 8, then invoke `/research-presentation ${OUTPUT_DIR}`. If no, proceed directly to Step 8.

### Step 8: Finalize & Clean Up (Director)

1. Cancel the `/loop` monitor (`CronDelete` on the cron ID captured when the loop was created).
2. Shut down each member:
   ```bash
   cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <researcher-agent-id>
   cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <scout-agent-id>
   cafleet --session-id <session-id> member delete --agent-id <director-agent-id> --member-id <manager-agent-id>
   ```
3. Tear down the session (this also deregisters the root Director and the Administrator — `cafleet deregister --agent-id <director-agent-id>` is rejected with `Error: cannot deregister the root Director; use 'cafleet session delete' instead.`):
   ```bash
   cafleet session delete <session-id>
   # → Deleted session <session-id>. Deregistered N agents.
   ```

`session delete` soft-deletes the `sessions` row and physically deletes every associated `agent_placements` row while preserving all `tasks` rows for audit — the message history remains inspectable in the admin WebUI.

$ARGUMENTS
