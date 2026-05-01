#!/usr/bin/env python3

import json
import re
import sys

_OPERATOR_PATTERN = re.compile(r"&&|>>|[;<>$`]")


def find_violation(command: str) -> str | None:
    match = _OPERATOR_PATTERN.search(command)
    return match.group() if match else None


def main() -> None:
    data = json.load(sys.stdin)
    if (violation := find_violation(data["tool_input"]["command"])) is not None:
        print(
            f"BLOCKED: Shell operator '{violation}' is not allowed. "
            "Use separate Bash calls instead of chaining.",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
