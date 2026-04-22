"""CLI entry: load env, run deterministic agent, print structured answer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from app.agent import run_agent
from app.prompts import PHASE1_DISCLAIMER, SYSTEM_POLICY_TEXT
from app.schemas import render_answer_for_cli

_ROOT = Path(__file__).resolve().parents[1]


def main(argv: Optional[List[str]] = None) -> int:
    load_dotenv(_ROOT / ".env")

    parser = argparse.ArgumentParser(
        description="US stock research assistant (phase 1: deterministic stubs).",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question words (joined with spaces).",
    )
    parser.add_argument(
        "-q",
        "--question",
        dest="question_flag",
        default=None,
        help="Question as a single string (overrides positional words).",
    )
    args = parser.parse_args(argv)

    if args.question_flag is not None:
        q = args.question_flag.strip()
    else:
        q = " ".join(args.question).strip()

    if not q:
        parser.error("Provide a question via positional words or -q/--question.")

    print(PHASE1_DISCLAIMER)
    print()
    print("Policy (summary):")
    for line in SYSTEM_POLICY_TEXT.splitlines():
        print(f"  {line}")
    print()

    _scope, answer = run_agent(q)
    print(render_answer_for_cli(answer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
