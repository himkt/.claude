---
name: agent-team-supervision
description: Mandatory supervision obligations for any agent acting as Director (team lead) in an in-process agent team. Load this skill before spawning any teammates. Defines team creation, spawn protocol, communication, idle semantics, user delegation, stall response, and cleanup.
---

# Agent Team Supervision (In-Process)

Load this skill via `Skill(agent-team-supervision)` before spawning any teammates.

## Core Principle

**You are the instruction giver. If you stop giving instructions, the entire team stops.**

Teammates respond to messages. They do not act autonomously. If you are not actively assigning tasks or replying to teammate messages, work halts silently.

## Team Infrastructure (MANDATORY)

Agent Teams require `TeamCreate` plus the `team_name` argument on every `Agent` call. **NEVER spawn teammates with plain `Agent()` calls that lack `team_name`.** Plain `Agent()` creates isolated subagents that cannot use `SendMessage`, cannot receive tasks, and cannot be coordinated — using one when a skill specifies Agent Teams is a violation of the skill specification.

**Required sequence — no exceptions:**

1. `TeamCreate(team_name="<team-name>", description="<purpose>")` — creates the team at `~/.claude/teams/<team-name>/config.json` and a shared task list at `~/.claude/tasks/<team-name>/`.
2. `Agent(subagent_type="<type>", team_name="<team-name>", name="<teammate-name>", prompt="<self-contained brief>")` — spawns each teammate and joins them to the team.

**Naming conventions:**

- `team-name`: kebab-case, reflects the skill and artifact (e.g. `create-auth-doc`, `execute-search-ranker`).
- Teammate `name`: the role (e.g. `drafter`, `reviewer`, `programmer`, `manager`, `researcher-1`). Always refer to teammates by name in `SendMessage(to: ...)` and `TaskUpdate(owner: ...)`.

**Subagent type selection:**

Match the agent type to the work. Read-only types (`Explore`, `Plan`) cannot edit or write files — assign them only to research / planning. Writing work needs `general-purpose` or a custom agent defined in `agents/*.md`.

## Communication Model

Your plain output is NOT visible to teammates. To communicate, call `SendMessage`. Teammate messages are delivered automatically as new conversation turns — you do NOT poll an inbox. When relaying, don't quote the original (already rendered to the user).

```json
{"to": "drafter", "summary": "deliver clarifying answers", "message": "User answered: 1) REST; 2) Postgres; 3) yes — include migrations."}
```

**Broadcast** (`"to": "*"`) is expensive (linear in team size) — use only when every teammate genuinely needs the information.

## Task-Based Coordination

Teams share a task list at `~/.claude/tasks/<team-name>/`. This is the primary coordination mechanism — not spawn prompts.

- Create tasks with `TaskCreate`, assign with `TaskUpdate(taskId, owner: "<teammate-name>")`.
- Teammates claim unassigned tasks (prefer lowest ID) and mark them completed.
- Use `addBlockedBy` / `addBlocks` to express dependencies (e.g. reviewer is blocked by drafter).
- Inspect state via `TaskList` and `TaskGet`.

Prefer tasks over ad-hoc spawn prompts for any work step that can be expressed as "do X and mark the task completed." Spawn prompts are for the initial brief; ongoing work flows through tasks + SendMessage.

## Idle Semantics (CRITICAL)

**Teammates go idle after every turn. Idle is normal, not a stall.** A teammate sending you a message and then going idle is the expected flow — they sent their output and are waiting for input.

- Idle teammates receive messages normally; sending a message wakes them.
- Idle notifications are informational. Do not react to them unless you are ready to assign new work.
- Peer DMs between teammates show a one-line summary in the idle notification — informational only.
- Do NOT comment on idleness or nudge a teammate just because they went idle. Only nudge when idleness **blocks your next step**.

## User Delegation Protocol

Teammates never talk to the user directly — you relay. When a teammate sends you a `SendMessage` asking for user input:

1. **Classify the question shape:**
   - Choice among labelled options → `AskUserQuestion` with up to 4 options mirroring the teammate's labels; built-in "Other" handles custom text. Do NOT add an explicit "Write my own" option.
   - Open-ended / draft selection → `AskUserQuestion` with 2–4 complete candidate bodies so the user can compare wording side-by-side.
   - Yes/no → two-option `AskUserQuestion`.
2. **Ask the user.** No preamble sentence above the question — the conversation context carries it.
3. **Relay the answer back** via `SendMessage` to the originating teammate. Pass through the user's selection verbatim; do not substitute your own judgment. If the user chose "Other" and typed custom text, send the typed text.

**What you MUST NOT do:**

- Decide on the user's behalf, even when the answer looks obvious.
- Batch multiple teammates' questions into a single `AskUserQuestion` unless they are genuinely the same decision.
- Summarize or paraphrase the user's answer when relaying — pass it through.

## Stall Response

A teammate is stalled when they **block your next step** — not merely because they are idle. Signals:

- The task they own is `in_progress` but they have sent nothing for long enough that the next dependent task cannot start.
- You sent a `SendMessage` and received no reply after a reasonable window.
- `TaskList` shows no owner progress and no new tasks created.

**Response ladder:**

1. Send a specific instruction via `SendMessage` — never a generic "are you OK?". State the deliverable and the blocker you are trying to unblock.
2. If still no reply after a second nudge, re-read the task via `TaskGet` to see if the teammate updated status or added a comment.
3. After 2 nudges without progress, escalate to the user via `AskUserQuestion` — do not silently kill the task.

## Monitoring

For skills with ≥2 teammates working in parallel, load `Skill(agent-team-monitoring)` and follow its `/loop` protocol for active stall detection. Simple linear handoffs (Director → Drafter → Reviewer → user) do not need a monitor — the stall response ladder above is enough.

## Cleanup Protocol

When the skill's work is approved by the user:

1. Send `SendMessage(to: "<teammate>", message: {"type": "shutdown_request"})` to each teammate. Approving shutdown terminates the teammate's process.
2. After all teammates have shut down, call `TeamDelete` to remove the team and task directories.
3. If a `/loop` monitor was running, cancel it with `CronDelete`.

**Order matters.** `TeamDelete` fails while any teammate is still active. Shutdown first, then delete.

## Quick Reference

| Action | Tool | Notes |
|---|---|---|
| Create team | `TeamCreate` | First step — before any `Agent` call |
| Spawn teammate | `Agent(team_name, name, subagent_type, prompt)` | Prompt must be self-contained |
| Message teammate | `SendMessage(to, summary, message)` | Auto-delivered, no polling |
| Assign task | `TaskUpdate(taskId, owner)` | Names, not UUIDs |
| Check team state | `TaskList`, `TaskGet` | Read-only inspection |
| Relay user input | `AskUserQuestion` → `SendMessage` | Pass-through; never substitute judgment |
| Shut down teammate | `SendMessage(..., message: {type: "shutdown_request"})` | Terminates teammate process |
| Delete team | `TeamDelete` | After all teammates shut down |
