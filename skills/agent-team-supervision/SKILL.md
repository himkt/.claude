---
name: agent-team-supervision
description: Mandatory supervision obligations for any agent acting as Director (team lead) in an agent team. Load this skill before spawning any teammates. Defines monitoring mandate, spawn protocol, and stall response.
---

# Agent Team Supervision

Load this skill via `Skill(agent-team-supervision)` before spawning any teammates.

## Core Principle

**You are the instruction giver. If you stop giving instructions, the entire team stops.**

Teammates do not act autonomously. They respond to your messages. If you are not actively monitoring and instructing, work halts silently.

## Monitoring Mandate

Before spawning ANY teammate, set up a `/loop` monitor using `Skill(loop)` or `/loop` with a 3-minute interval. The loop prompt must:

1. Check the output directory for expected deliverable files
2. Compare found files against the expected set
3. Message any teammate whose deliverable is missing: "Report your progress now. If blocked, state what is blocking you."
4. Message the Director (team-lead) when all deliverables exist: "All deliverables are ready for review."

**Lifecycle:** The loop MUST stay active from the first teammate spawn until the final shutdown (`CronDelete` only in the cleanup step). It must run through all phases: research, compilation, review, revision, user approval.

## Spawn Protocol

Every time you spawn a teammate:

1. Ensure the `/loop` monitor is already running (set it up if not)
2. Spawn the teammate
3. Verify the teammate is active

Never spawn teammates without an active monitor. Never cancel the monitor until all work is fully complete and the team is being shut down.

## Stall Response

When you receive any signal that a teammate may be stalled (loop check, idle notification, user nudge), evaluate immediately whether the teammate is working, blocked, or dead. You have two channels to inspect their state — always try `SendMessage` first, and fall back to `tmux capture-pane` when no reply comes back (a busy teammate often cannot reply mid-task):

- SendMessage: send a specific instruction directly to the teammate, never a generic "are you OK?" (interactive and authoritative, but blocks on the teammate actually responding — which may not happen while they are mid-task)
- tmux capture-pane: snapshot the teammate's pane with `tmux capture-pane -p -t <pane> -S -<lines>` to see exactly what they are doing right now (non-intrusive read-only inspection; works even when the teammate is too busy to respond to messages). Use `tmux ls` to find the pane name.

If a teammate is still unresponsive after 2 nudges (and `tmux capture-pane` shows no forward progress), escalate to the user.
