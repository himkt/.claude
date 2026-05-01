---
name: research-report
description: Create a comprehensive research report with folder-based output. Researchers write findings to individual files, the Manager compiles report.md, and the Director reviews. Output goes to researches/<topic-slug>/. After report approval, offers to chain into /research-presentation for slides and transcript. Teammates must always load skills using the Skill tool, not by reading skill files directly. Do NOT do a quick web search and summarize — invoke this skill for thorough, multi-source research.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet
---

# Research Report

Generate comprehensive research reports using a multi-layer in-process agent team: Director → Manager → Scouts/Researchers. Every member of the team carries serious accountability for the quality of the final deliverable, and the team iterates relentlessly until the report meets the highest standard. After the report is approved, the Director offers to chain into `/research-presentation` for slides and transcript.

| Role | Identity | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Create team, spawn all teammates, relay Manager requests, review all deliverables, present to user | Write the report, decompose topics, conduct research | [roles/director.md](roles/director.md) |
| **Manager** | `general-purpose` teammate | Run orientation searches for landscape understanding and topic decomposition, request Scout/Researcher spawning from the Director, aggregate Scout and Researcher findings, compile report, revise | Conduct deep investigation — all substantive research MUST be delegated to Researchers | [roles/manager.md](roles/manager.md) |
| **Scout** | `Explore` teammate | Landscape mapping — broad discovery to expand knowledge before decomposition | Collect facts for the report, write report sections | [roles/scout.md](roles/scout.md) |
| **Researcher** | `web-researcher` teammate | Search exhaustively, collect facts with sources, filter misinformation, write findings to assigned file | Synthesize or write report sections | [roles/researcher.md](roles/researcher.md) |

## Additional resources

- For the report format specification, see [template.md](template.md)

## Architecture

The Director creates an in-process team with `TeamCreate`, spawns the Manager, and spawns every Scout and Researcher with `Agent(team_name=..., name=...)`. All coordination goes through `SendMessage` (auto-delivered) and a shared task list.

```
User
 +-- Director (main Claude — TeamCreate, Agent spawn, SendMessage orchestration)
      +-- Manager (teammate: general-purpose — compiles the report)
      +-- Scout 1..N (teammates: Explore — spawned by Director on Manager's request)
      +-- Researcher 1..N (teammates: web-researcher — spawned by Director on Manager's request)
```

- **Director ↔ User**: `AskUserQuestion` (final report presentation, feedback collection)
- **Director ↔ Manager**: `SendMessage` (spawn requests, review feedback, shutdown)
- **Director ↔ Scouts / Researchers**: `SendMessage` (assignment relays, findings reports, revision requests)
- **Manager → Director**: spawn requests via `SendMessage` for Scouts and Researchers

Teammates cannot talk to the user directly — the Director always relays. Teammates cannot talk to each other directly either — Manager requests are always mediated by the Director (Manager → Director → Scout/Researcher, and Scout/Researcher → Director → Manager).

## Process

### Step 0: Base Directory Selection (Director)

Before creating the team, determine where output files will be saved.

1. Load `Skill(base-dir)` and follow its procedure. (The topic argument is not a path, so the absolute-path skip rule does not apply.)
2. Compute: `${OUTPUT_DIR} = ${BASE}/researches/<topic-slug>/`
3. Create the output directory.
4. Pass `${OUTPUT_DIR}` as the resolved absolute path to the Manager and all Researchers/Scouts in their spawn prompts.

### Step 1: Start Progress Monitor (Director — MANDATORY)

Load `Skill(agent-team-supervision)` and `Skill(agent-team-monitoring)`. Start a `/loop` monitor BEFORE the first `Agent(team_name=...)` call so the first tick fires while spawning completes.

The loop must check `${OUTPUT_DIR}` for these expected deliverables:

- `report.md` — required final compiled report from the Manager
- `00-scout-*.md` — Scout landscape/discovery notes (one or more files may exist)
- `NN-research-*.md` — Researcher findings files for delegated sub-topics (`NN` is the assigned number; one or more files may exist)

Readiness/stall rules (apply per `Skill(agent-team-monitoring)`):

- After Scouts/Researchers have been spawned and tasks have been assigned, expect at least one `00-scout-*.md` or `NN-research-*.md` file to appear within a couple of ticks.
- Do not consider the workflow ready for Step 5 until `report.md` exists.
- If a teammate owns an `in_progress` task but their deliverable file is missing past the expected milestone, run the health-check sequence (`TaskList` inspection → directed `SendMessage` nudge → user escalation) from `Skill(agent-team-monitoring)`.
- Keep the monitor running until Step 8.

### Step 2: Create Team & Spawn Manager (Director)

Load `Skill(agent-team-supervision)` and follow its spawn protocol.

#### 2a. Create the team

```
TeamCreate(team_name="research-<topic-slug>", description="Research report: <topic-slug>")
```

This creates the shared task list at `~/.claude/tasks/research-<topic-slug>/` that the team will use for coordination.

#### 2b. Read role definitions

Read the role files that will be embedded verbatim in spawn prompts:

- `~/.claude/skills/research-report/roles/manager.md`
- `~/.claude/skills/research-report/roles/scout.md`
- `~/.claude/skills/research-report/roles/researcher.md`

#### 2c. Spawn the Manager

**Manager spawn prompt:**

```
You are the Manager in a research report team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-report/roles/manager.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(agent-team-supervision) — for team/message fundamentals (idle semantics, shutdown)

CURRENT DATE: [INSERT today's date]
USER REQUEST: [INSERT user's original request in full]
OUTPUT DIRECTORY: [INSERT ${OUTPUT_DIR}]
LANGUAGE: [INSERT user's language preference if specified]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- You do NOT talk to Scouts or Researchers directly. The Director spawns them and relays their findings.
- Messages from the Director arrive automatically — you do not poll.
- The team shares a task list (TaskList / TaskGet / TaskUpdate). Use it to track sub-topic assignments.

To request Scouts or Researchers, SendMessage the Director specifying: role (Scout or Researcher), scope, search angles, and output file path. The Director will spawn them and relay their completion reports back to you.

Your first compiled report will be reviewed critically by the Director. Aim for highest quality on the first attempt.
```

Spawn with:

```
Agent(
  subagent_type="general-purpose",
  team_name="research-<topic-slug>",
  name="manager",
  prompt="<Manager spawn prompt with embedded role content>"
)
```

### Step 3: Knowledge Bootstrapping — Scout Phase (Director, on Manager's request)

After assessing the topic, the Manager may send the Director one or more Scout spawn requests via `SendMessage`. For each request, the Director spawns a Scout.

**Scout spawn prompt:**

```
You are a Scout Researcher in a research team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-report/roles/scout.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(agent-team-supervision) — for team/message fundamentals
- Also Read ~/.claude/agents/web-researcher.md for the detailed research methodology
  (Discovery Phase, query formulation, synthesis, output format)

CURRENT DATE: [INSERT today's date]
YOUR ASSIGNMENT: [landscape scope and what areas to map]
OUTPUT FILE: [INSERT <resolved-path>/00-scout-<topic>.md]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- Messages from the Director arrive automatically.

Write findings to the output file, then SendMessage the Director with a completion summary. The Director will relay your findings to the Manager.
```

Spawn with:

```
Agent(
  subagent_type="Explore",
  team_name="research-<topic-slug>",
  name="scout-<NN>",
  prompt="<Scout spawn prompt>"
)
```

(Use `scout` if only one; `scout-1`, `scout-2`, ... for multiple.)

**Scout-Manager loop (relayed through Director):**

1. Manager sends Director a Scout spawn request (`SendMessage`).
2. Director spawns the Scout via `Agent(team_name=..., name="scout-<NN>")`.
3. Scout investigates, writes findings to the output file, `SendMessage(to: "director")` with a completion report.
4. Director relays the Scout's output file path (and any summary text) to the Manager via `SendMessage`.
5. Manager reads the Scout file and may send a follow-up request (either targeted re-scouting, a new Scout, or proceed to decomposition).

**Safety cap**: Maximum 3 Scout-Manager iterations (request → investigate → review = one iteration). After 3 iterations, the Manager must proceed to topic decomposition with the knowledge gathered so far.

### Step 4: Spawn Researchers (Director, on Manager's request)

After decomposing the topic, the Manager sends the Director one or more Researcher spawn requests via `SendMessage`.

#### 4a. Create tasks for each sub-topic (Manager, before spawn requests)

With multiple Researchers running in parallel, coordination goes through the **shared task list** — not just through spawn prompts. The Manager MUST create one task per sub-topic BEFORE asking the Director to spawn the Researcher for it.

- The Manager calls `TaskCreate` for each sub-topic. Task content describes the sub-topic, scope, and the expected output file path (e.g., `<resolved-path>/01-research-<subtopic>.md`).
- Tasks start unowned. When a Researcher is spawned and given their assignment, they claim their assigned task by calling `TaskUpdate(taskId, owner: "researcher-<NN>")` and marking it `in_progress`.
- Researchers mark their task `completed` when their output file is written and the completion report has been sent.
- The Manager blocks on all research tasks being `completed` before starting compilation. Use `TaskList` to check progress.

The Manager's `TaskCreate` calls also serve as the authoritative list of sub-topic scopes — if the Director sees a discrepancy between a spawn request's scope and the corresponding task, treat the task description as canonical and ask the Manager to reconcile.

#### 4b. Spawn each Researcher (Director)

**Researcher spawn prompt:**

```
You are a Research Specialist in a research team.

<ROLE DEFINITION>
[Content of ~/.claude/skills/research-report/roles/researcher.md injected verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(agent-team-supervision) — for team/message fundamentals
- Also Read ~/.claude/agents/web-researcher.md for the detailed research methodology
  (Discovery Phase, query formulation, synthesis, output format)

CURRENT DATE: [INSERT today's date]
YOUR NAME: researcher-<NN>
YOUR ASSIGNMENT: [specific sub-topic and what to investigate]
YOUR TASK ID: [INSERT the taskId the Manager created for this sub-topic]
OUTPUT FILE: [INSERT <resolved-path>/NN-research-<subtopic>.md]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- Messages from the Director arrive automatically.
- On start, claim your task: TaskUpdate(taskId: YOUR TASK ID, owner: "researcher-<NN>", status: "in_progress").
- On completion, mark your task completed: TaskUpdate(taskId: YOUR TASK ID, status: "completed").

Write findings to the output file, then SendMessage the Director with a completion summary. The Director will relay findings and any follow-up questions between you and the Manager.
```

Spawn with:

```
Agent(
  subagent_type="web-researcher",
  team_name="research-<topic-slug>",
  name="researcher-<NN>",
  prompt="<Researcher spawn prompt>"
)
```

The Director repeats this step whenever the Manager requests additional Researchers (for coverage gaps, failed investigations, or revision-driven re-research). Any new Researcher must first have a task created by the Manager; the Director includes the `taskId` in the spawn prompt.

### Step 5: Review & Revision Loop (Director ↔ Manager, via `SendMessage`)

When the Manager delivers the compiled `report.md`:

1. The Director reads `${OUTPUT_DIR}/report.md` and reviews it critically against the checklist in [roles/director.md](roles/director.md).
2. The Director sends tagged feedback to the Manager via `SendMessage`:
   ```
   SendMessage(to: "manager", summary: "review feedback round <N>", message: "[FACTUAL ERROR] ... / [GAP] ... / ...")
   ```
3. The Manager revises the report (requesting additional Researchers from the Director as needed) and `SendMessage`s a completion message back.
4. Repeat until the Director judges quality is sufficient. Aim for 2–3 rounds maximum.

If the Manager asks the Director a question that is really a user decision (e.g. language choice, scope trade-off), the Director MUST relay via `AskUserQuestion` per the user-delegation protocol in `Skill(agent-team-supervision)`. Never decide on the user's behalf.

### Step 6: Present to User (Director)

Present the approved report to the user via `AskUserQuestion` with: a summary of findings (2–3 sentences), file paths (report, scout files, researcher files), known limitations, and a request for feedback. If the user provides feedback, route it to the Manager via `SendMessage`, re-review, and re-present. Repeat until the user approves.

### Step 7: Offer Presentation Chaining (Director)

After user approval, offer to create a presentation via `AskUserQuestion` (adapt to user's language). If yes, proceed to Step 8, then invoke `/research-presentation ${OUTPUT_DIR}`. If no, proceed directly to Step 8.

### Step 8: Finalize & Clean Up (Director)

Follow the cleanup protocol in `Skill(agent-team-supervision)`:

1. Cancel the `/loop` monitor with `CronDelete`.
2. Shut down each teammate:
   ```
   SendMessage(to: "researcher-<NN>", message: {"type": "shutdown_request"})   # for each researcher
   SendMessage(to: "scout-<NN>", message: {"type": "shutdown_request"})         # for each scout (if any still active)
   SendMessage(to: "manager", message: {"type": "shutdown_request"})
   ```
3. After all teammates have shut down, call `TeamDelete` to remove the team and task directories.

`TeamDelete` fails while any teammate is still active, so order matters: shutdown first, then delete.

$ARGUMENTS
