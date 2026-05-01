---
name: design-doc-create
description: Create a new design document. Use when user wants to create a specification or technical document. Do NOT use EnterPlanMode — always invoke this skill instead.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet
---

# Design Doc Create

Create high-quality design documents using a three-role in-process agent team: Director (orchestrator), Drafter (writes the document), and Reviewer (critically reviews drafts). The team iterates through an internal quality loop before presenting a polished draft to the user.

| Role | Identity | Does | Does NOT | Role definition |
|:--|:--|:--|:--|:--|
| **Director** | Main Claude | Create team, spawn teammates, relay user answers, enforce clarification gate, orchestrate internal quality loop, present polished draft to user | Write the document, review it in detail | [roles/director.md](roles/director.md) |
| **Drafter** | `design-doc-creator` teammate | Ask clarifying questions (via Director relay), read target codebase, write and revise the design document | Communicate with user directly (goes through Director), review own work | [roles/drafter.md](roles/drafter.md) |
| **Reviewer** | `general-purpose` teammate | Critically review drafts for rule compliance, readability, completeness, correctness | Write the document, communicate with user | [roles/reviewer.md](roles/reviewer.md) |

## Additional resources

- For the document template, see: [../design-doc/template.md](../design-doc/template.md)
- For section guidelines and quality standards, see: [../design-doc/guidelines.md](../design-doc/guidelines.md)

## Architecture

The Director creates an in-process team with `TeamCreate` and spawns both teammates with `Agent(team_name=..., name=...)`. All coordination goes through `SendMessage` (auto-delivered) and the shared task list.

```
User
 +-- Director (main Claude — TeamCreate, Agent spawn, SendMessage orchestration)
      +-- Drafter (teammate: design-doc-creator — writes the design document)
      +-- Reviewer (teammate: general-purpose — critically reviews the draft)
```

- **Director ↔ User**: `AskUserQuestion` (clarification relay, draft presentation, feedback collection)
- **Director ↔ Drafter**: `SendMessage` (questions relay, user answers, reviewer feedback, drafting instructions)
- **Director ↔ Reviewer**: `SendMessage` (draft review requests, review feedback)

Teammates cannot talk to the user directly — the Director always relays.

## Process

### Step 0: Path Resolution & Resume Detection (Director)

**Path resolution** (before resume detection):

Load `Skill(base-dir)` and follow its procedure with `$ARGUMENTS` as the argument.
- If skipped (absolute path): set `${DOC_PATH} = $ARGUMENTS`.
- If base resolved: set `${DOC_PATH} = ${BASE}/design-docs/$ARGUMENTS`. Resolve to absolute path.

Pass `${DOC_PATH}` to the Drafter as OUTPUT PATH in the spawn prompt.

**Resume detection** (using resolved `${DOC_PATH}`):

1. **File does not exist** → Fresh creation (proceed to Step 1 as normal).
2. **File exists** → Check for COMMENT markers:
   - Use Grep to search for `COMMENT(` in the file.
   - **COMMENT markers found** → This is **resume mode**. Proceed to Step 1 with the resume-specific Drafter spawn prompt. Set `SKIP_CLARIFICATION=true` so Step 2 is skipped.
   - **No COMMENT markers found** → Inform the user: "No COMMENT markers found in the existing document." Use `AskUserQuestion` with two options:
     - **"Run quality review"**: Set `SKIP_CLARIFICATION=true` and `QUALITY_REVIEW_ONLY=true`. Skip Step 2 entirely and enter Step 3 by routing the existing `${DOC_PATH}` to the Reviewer (no new draft is produced; the Drafter is only involved later if the Reviewer requests revisions).
     - **"Start fresh"**: Treat as new creation, ignoring the existing file. Ensure `SKIP_CLARIFICATION` and `QUALITY_REVIEW_ONLY` are unset, then proceed to Step 1 as normal.

### Step 1: Create Team & Spawn Teammates (Director)

Load `Skill(agent-team-supervision)` and follow its spawn protocol.

#### 1a. Create the team

```
TeamCreate(team_name="create-<doc-slug>", description="Design doc creation: <doc-slug>")
```

#### 1b. Read role definitions

Read the role files that will be embedded in spawn prompts:

- `~/.claude/skills/design-doc-create/roles/drafter.md`
- `~/.claude/skills/design-doc-create/roles/reviewer.md`

#### 1c. Spawn the Drafter

**Drafter spawn prompt (normal mode):**

```
You are the Drafter in a design document creation team.

<ROLE DEFINITION>
[Content of roles/drafter.md injected here verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(design-doc) — for template and guidelines

OUTPUT PATH: [INSERT ${DOC_PATH}]

The user's request: [INSERT USER'S ORIGINAL REQUEST]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- You do NOT talk to the user directly. The Director relays.
- Messages from the Director arrive automatically — you do not poll.

IMPORTANT: You MUST ask clarifying questions BEFORE writing any design document file.
Start by reading the target codebase for context, then SendMessage your clarifying questions to the Director.
Do NOT create any design document file until you have received answers.
```

Spawn with:

```
Agent(
  subagent_type="design-doc-creator",
  team_name="create-<doc-slug>",
  name="drafter",
  prompt="<Drafter spawn prompt>"
)
```

**Drafter spawn prompt (resume mode):**

Use this instead when Step 0 detected resume mode:

```
You are the Drafter in a design document creation team (RESUME MODE).

<ROLE DEFINITION>
[Content of roles/drafter.md injected here verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(design-doc) — for template and guidelines

DESIGN DOCUMENT: [INSERT ${DOC_PATH}]

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- Messages from the Director arrive automatically.

This is a RESUME session. The document contains COMMENT markers from a previous
interview. Follow the Resume Mode instructions in your role definition.
Do NOT ask clarifying questions — the COMMENTs contain the needed information.
Start by reading the design document.
```

#### 1d. Spawn the Reviewer

**Reviewer spawn prompt:**

```
You are the Reviewer in a design document creation team.

<ROLE DEFINITION>
[Content of roles/reviewer.md injected here verbatim]
</ROLE DEFINITION>

Load these skills at startup:
- Skill(design-doc) — for template and guidelines

COMMUNICATION PROTOCOL:
- You talk to the Director via SendMessage(to: "director", summary: "...", message: "...").
- Messages from the Director arrive automatically.

Wait for the Director to assign a document for review. Read the document file and
provide specific, actionable feedback. If the draft meets all quality standards,
signal: "APPROVED - Ready for user review."
```

Spawn with:

```
Agent(
  subagent_type="general-purpose",
  team_name="create-<doc-slug>",
  name="reviewer",
  prompt="<Reviewer spawn prompt>"
)
```

### Step 2: Clarification Phase (Director)

**Skip this step entirely when `SKIP_CLARIFICATION=true`** (resume mode or quality-review-only mode).

1. Wait for the Drafter's clarifying-questions `SendMessage` — it arrives automatically as a new conversation turn.
2. Relay the questions to the user via `AskUserQuestion`. If the number of questions exceeds the per-call limit of `AskUserQuestion`, split them into multiple sequential calls to relay all questions without omission.
3. Relay the user's answers back:
   ```
   SendMessage(to: "drafter", summary: "clarifying answers", message: "User answers: ...")
   ```
4. **Gate check**: If the Drafter produces a draft without prior questions, reject it:
   ```
   SendMessage(to: "drafter", summary: "reject premature draft", message: "Stop — you must send clarifying questions before drafting. Discard the draft and send questions first.")
   ```
   A focused confirmation round counts as valid clarification.

### Step 3: Internal Quality Loop (Director)

Enter this step after the Drafter reports a completed draft, **or immediately** when `QUALITY_REVIEW_ONLY=true` (the existing `${DOC_PATH}` is treated as the "completed draft").

1. **Route to Reviewer** with the document path:
   ```
   SendMessage(to: "reviewer", summary: "review request", message: "Please review the draft at ${DOC_PATH}. Provide feedback or signal APPROVED.")
   ```
2. **Wait** for the Reviewer's feedback message.
3. **On feedback**: Route to Drafter for revision:
   ```
   SendMessage(to: "drafter", summary: "reviewer feedback", message: "Reviewer feedback: ... Please address and reply when done.")
   ```
4. Wait for the Drafter's revision message, then loop back to step 1.
5. Repeat until the Reviewer explicitly signals `APPROVED - Ready for user review.`
6. **Iteration limit**: Aim for 2–3 rounds. If not converging, escalate to the user: summarize the remaining issues and use `AskUserQuestion` to ask whether to continue iterating or abort. Do not proceed to Step 4 until the Reviewer has approved.

### Step 4: Present to User (Director)

Only after the Reviewer explicitly approves, present a summary (including file path) and use `AskUserQuestion`:

| Option | Label | Description | Behavior |
|:--|:--|:--|:--|
| 1 | **Approve** | Proceed with the current result | Proceed to finalization (Step 6) |
| 2 | **Scan for COMMENT markers** | Immediately scan the document for `COMMENT(name): feedback` markers and process them | Scan immediately and process markers (see Step 5) |
| 3 | *(Other — built-in)* | *(Free text input)* | Interpret user intent (see Step 5) |

See [roles/director.md](roles/director.md) for user interaction rules (COMMENT handling, intent judgment, abort detection).

### Step 5: User Feedback Loop (Director)

Process the user's selection:

- **"Scan for COMMENT markers"**:
  1. **Immediately** scan the document with Grep for `COMMENT(` markers — do NOT wait for the user to confirm they are done editing.
  2. **If markers are found**: Route COMMENT content and fix instructions to the Drafter via `SendMessage`. After the Drafter revises and removes markers, verify with Grep that no `COMMENT(` markers remain. Then re-enter the quality loop (Step 3) and re-present (Step 4).
  3. **If no markers are found**: Explain the COMMENT marker convention — markers follow the pattern `# COMMENT(username): feedback` placed directly in the design document file. Show the file path. Re-prompt with the same three-option pattern.

- **"Other" (free text)**: Use LLM reasoning to distinguish:
  - **Abort intent** → Trigger the Abort Flow: follow the Shutdown Protocol (Step 6) without Drafter finalization.
  - **Non-abort intent** (verbal feedback / question) → Explain that feedback should be provided via COMMENT markers, then re-prompt.

No round limit — loop continues until approved or aborted.

### Step 6: Finalize & Clean Up (Director)

1. Instruct the Drafter to finalize:
   ```
   SendMessage(to: "drafter", summary: "finalize", message: "User approved. Please finalize: set Status to Approved, refresh Last Updated, bump the Progress header field if present in the template, verify implementation steps are actionable, then reply done.")
   ```
   Wait for the Drafter's confirmation.

2. Shut down teammates:
   ```
   SendMessage(to: "drafter", message: {"type": "shutdown_request"})
   SendMessage(to: "reviewer", message: {"type": "shutdown_request"})
   ```

3. `TeamDelete` — removes team and task directories.

$ARGUMENTS
