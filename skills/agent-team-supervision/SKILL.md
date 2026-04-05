---
name: agent-team-supervision
description: Mandatory supervision obligations for any agent acting as Director (team lead) in an agent team. Load this skill before spawning any teammates. Defines monitoring mandate, spawn protocol, and stall response.
allowed-tools: Read
---

# Agent Team Supervision

Load this skill via `Skill(agent-team-supervision)` before spawning any teammates.

## Core Principle

**You are the instruction giver. If you stop giving instructions, the entire team stops.**

Teammates do not act autonomously. They respond to your messages. If you are not actively monitoring and instructing, work halts silently.

## Monitoring Mandate

Before spawning ANY teammate, set up a `/loop` monitor using `Skill(loop)` with a 3-minute interval. The loop prompt must:

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

When you receive any signal that a teammate may be stalled (loop check, idle notification, user nudge):

- Evaluate immediately: Is the teammate working, blocked, or dead?
- Send a specific instruction, not a generic "are you OK?"
- If a teammate is unresponsive after 2 nudges, escalate to the user
