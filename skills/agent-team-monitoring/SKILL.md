---
name: agent-team-monitoring
description: Active-monitoring `/loop` protocol for agent team Directors with parallel teammates. Defines the health-check sequence (deliverable scan, TaskList inspection, SendMessage ping, escalation) and loop lifecycle. Load alongside agent-team-supervision when ≥2 teammates work in parallel.
---

# Agent Team Monitoring

Load this skill via `Skill(agent-team-monitoring)` when your team has ≥2 teammates working in parallel, or any phase that runs long enough that a silent stall would waste real wall time.

For the spawn / communication / cleanup fundamentals, see `Skill(agent-team-supervision)` — this skill assumes you are already a Director on an active team.

## When to Run a Monitor

Use a `/loop` monitor when any of these hold:

- Two or more teammates run in parallel (e.g. multiple researchers, or programmer + tester).
- A single teammate runs a long task (> ~3 minutes expected wall time) while you have other coordination work to do.
- A teammate owns a task whose output is the blocking input for the next phase.

Skip the monitor for strictly linear handoffs (Drafter → Reviewer → user). The stall-response ladder in `Skill(agent-team-supervision)` is enough for linear flow.

## Core Principle

Monitoring is ACTIVE, not passive. Teammate idleness alone is not a signal — per `Skill(agent-team-supervision)`, idle is the normal between-turn state. A monitor fires only on signals that idleness is **blocking progress**:

- Expected deliverable file is missing.
- Task marked `in_progress` but task body / comments show no recent owner update.
- Another teammate needs the output and cannot proceed.

## Health-Check Sequence

Run this sequence once per `/loop` tick. Order matters — cheapest non-intrusive check first, most invasive last.

### 1. Deliverable scan (file-based)

For each expected deliverable file (skill-specific — e.g. `doc.md`, `report.md`, `researches/<slug>/researcher-*.md`), check existence and mtime via `Glob` + `Read` (first ~50 lines).

- File exists and looks complete → mark that teammate's lane green.
- File missing past its milestone → candidate stall, continue to step 2.

### 2. Task state inspection

Call `TaskList` and examine tasks whose owner is a teammate.

- `in_progress` + recent `updated_at` → teammate is working, no action.
- `in_progress` + stale `updated_at` (no update for > 2 loop ticks) → candidate stall, continue to step 3.
- `pending` with owner assigned → teammate has not picked up; nudge in step 3.
- `completed` but deliverable missing → teammate marked done without producing output; hard stall, go straight to step 4.

### 3. Directed nudge

`SendMessage` the teammate with a specific, actionable message:

- State the deliverable you expected.
- State the blocker (what downstream task cannot start).
- Ask for a concrete next action, not "are you OK?".

Example:

```json
{
  "to": "researcher-2",
  "summary": "researcher-2 deliverable missing",
  "message": "Your task #3 (researcher-2.md on Topic B) is in_progress but the file doesn't exist yet. Manager is blocked on compilation. Send your current status — what section are you on, and is anything blocking you?"
}
```

Do NOT:

- Ping immediately on the first missing-deliverable signal; give ≥1 full loop tick first.
- Send a generic "progress?" ping — it signals low trust and rarely produces useful information.
- Broadcast the nudge (`to: "*"`); nudge only the owner of the stalled task.

### 4. Escalate to user

If the teammate has been nudged twice across successive ticks and still has no output, stop the loop and escalate via `AskUserQuestion` with concrete options:

1. Re-spawn the teammate with a reset prompt.
2. Redistribute the task to another teammate.
3. Drop the task from scope.
4. (Other — user describes what to do.)

Do NOT silently `shutdown_request` or re-spawn the teammate without user input — the user might know something (flaky network, intentional pause) you don't.

## `/loop` Prompt Template

Use `Skill(loop)` with a 1–3 minute interval. Recommended: 2 minutes. The loop prompt must be self-contained (loop fires as a fresh turn) and invoke this skill:

```
Skill(agent-team-monitoring) — tick for team "<team-name>".

Expected deliverables:
- <path-1> by <milestone>
- <path-2> by <milestone>
- ...

Active teammates: <name-1>, <name-2>, ...

Run the 4-step health-check sequence. Nudge stalled owners with specific messages.
Escalate to the user after 2 consecutive stalled ticks on the same task.
Terminate the loop once all deliverables exist AND the user has approved the final artifact.
```

## Loop Lifecycle

| Phase | Action |
|---|---|
| Spawn teammates | Start the `/loop` BEFORE the first `Agent(team_name=...)` call, so the first tick fires while spawning completes |
| Run work | Loop ticks every 1–3 min; do not intervene unless a tick escalates |
| User review | Keep the loop alive during the review cycle — revisions and re-reviews still count as in-progress work |
| User approves final artifact | Loop terminates itself (final tick confirms approval, then `CronDelete`) |

**Never cancel the loop early** — premature cancellation is the primary cause of silent mid-flight stalls.

## Interaction With User Delegation

Monitoring and user delegation interact. When a teammate sends a message requesting user input (per the protocol in `Skill(agent-team-supervision)`), that is NOT a stall — it is the teammate waiting for you to relay. Do NOT nudge a teammate who has asked you a question and is waiting for the reply.

Clear signal: if the last message in the conversation from that teammate was a question addressed to you, mark their lane green for this tick regardless of task state.

## Cleanup

When the Director confirms final user approval:

1. Cancel the `/loop` with `CronDelete`.
2. Follow the cleanup protocol in `Skill(agent-team-supervision)` (shutdown teammates, then `TeamDelete`).

Cancelling the loop is a hard prerequisite of teardown — a live loop that outlives the team will fire against a deleted task list and produce confusing errors.
