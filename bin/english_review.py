#!/usr/bin/env python3
"""English-review Stop hook. Samples 10% of sessions and appends suggestions to a daily log."""

import json
import os
import pathlib
import random
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone

SAMPLE_RATE = 0.1
MODEL = "claude-opus-4-7"
LOG_ROOT = pathlib.Path("/tmp/claude-english-review-hook-logs")
LOG_DIR = LOG_ROOT / "logs"
ERROR_LOG_DIR = LOG_ROOT / "errors"
ERROR_LOG = ERROR_LOG_DIR / "errors.log"
NO_ENGLISH_SENTINEL = "NO_ENGLISH_CONTENT"

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

PROMPT_TEMPLATE = """\
You are reviewing the user's English writing from a chat transcript. \
Ignore the assistant's replies; focus only on the user-authored text below.

Review criteria:
- Grammar and syntax errors
- Naturalness and idiomatic phrasing
- Word choice and precision
- Clarity and concision

Output rules:
- Output ONLY a markdown bullet list of concrete suggestions.
- Each bullet: quote the original phrase in backticks, then suggest a revision and briefly say why.
- If the transcript contains no English content worth reviewing (e.g., it is entirely in another language, or only trivial greetings), output exactly this single line and nothing else:
{sentinel}
- Do NOT add headers, preamble, or closing remarks. Bullets only.

--- USER TEXT BEGINS ---
{user_text}
--- USER TEXT ENDS ---
"""

SYSTEM_PROMPT = (
    "You are a writing assistant that reviews English text. "
    "You have no tools available. Output only what the user asks for, in the format they specify."
)


def extract_user_text(transcript_path: pathlib.Path) -> str:
    parts: list[str] = []
    with transcript_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "user":
                continue
            msg = rec.get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text")
                        if isinstance(text, str):
                            parts.append(text)
    joined = "\n\n".join(p for p in parts if p)
    return _FENCE_RE.sub("[code omitted]", joined).strip()


def run_review(user_text: str) -> str:
    prompt = PROMPT_TEMPLATE.format(sentinel=NO_ENGLISH_SENTINEL, user_text=user_text)
    env = {**os.environ, "ENGLISH_REVIEW_HOOK_IN_PROGRESS": "1"}
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--model", MODEL,
            "--system-prompt", SYSTEM_PROMPT,
            "--no-session-persistence",
            "--tools", "",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--disable-slash-commands",
            "--settings", '{"disableAllHooks": true}',
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def append_entry(session_id: str, review: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    log_path = LOG_DIR / f"{today}.md"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    header = f"## {ts} (session {session_id[:8]})\n\n"
    entry = f"{header}{review}\n\n---\n\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def log_error() -> None:
    try:
        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now(timezone.utc).isoformat(timespec='seconds')} ---\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass  # last-resort swallow


def main() -> None:
    try:
        if os.environ.get("ENGLISH_REVIEW_HOOK_IN_PROGRESS"):
            return  # spawned by our own claude -p call; break the recursion
        if random.random() >= SAMPLE_RATE:
            return
        data = json.load(sys.stdin)
        if data.get("stop_hook_active"):
            return
        transcript_path = pathlib.Path(data["transcript_path"])
        session_id = data["session_id"]
        user_text = extract_user_text(transcript_path)
        if not user_text:
            return
        review = run_review(user_text)
        if not review or review == NO_ENGLISH_SENTINEL:
            return
        append_entry(session_id, review)
    except Exception:
        log_error()
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
