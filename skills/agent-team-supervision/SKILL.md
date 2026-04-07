---
name: agent-team-supervision
description: Director's monitoring mandate and stall protocol for agent teams. Load before spawning any teammate.
---

# Agent Team Supervision

Load this skill via `Skill(agent-team-supervision)` before spawning any teammates.

## Core Principle

**You are the instruction giver. If you stop giving instructions, the entire team stops.**

Teammates do not act autonomously. They respond to your messages. If you are not actively monitoring and instructing, work halts silently.

## Monitoring methods

- **`/loop` monitor** — recurring check (3-min interval) that compares deliverable files against the expected set and pings missing ones. Set up via `Skill(loop)` BEFORE spawning any teammate; cancel only at cleanup (`CronDelete`). Must stay active across all phases (research, compile, review, revise, approval).
- **`tmux capture-pane -p -t %<id> -S -30`** — direct pane inspection. Read `tmuxPaneId` from team config. A spinner (`Cultivating…`, `Forging…`) means working; an empty `❯` means idle. Use this to verify state before deciding to message — nudges cost teammate context.

## Communication methods

- **`SendMessage`** — the only way to instruct teammates. Always specific, never "are you OK?".
- **Never** use `tmux send-keys` to drive a teammate.

## Spawn protocol

Ensure `/loop` is running, then spawn, then verify active. No teammate without an active monitor.

## Stall response

On any stall signal (loop ping, idle notification, user nudge): inspect the pane first, send a specific instruction if truly idle, escalate to the user after 2 unanswered nudges.
