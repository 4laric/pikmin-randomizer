"""Generate the wave-wide dry-run admission advance report (lane 02, #438).

Reads every ``docs/PIKMIN2_LANE<NN>_DEEPSEEK_HANDOFF.md`` from a git branch
(via ``git show``), dry-runs the admission ingestion against the committed
roster, and writes a deterministic report to
``docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md``.

Lane 01 re-runs it after each merge so the report tracks the current wave:

    py -3.12 scripts/generate_p2_advance_report.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.ingest_p2_handoff_gates import (  # noqa: E402
    build_advance_report,
    render_advance_report,
)

_HANDOFF_RE = re.compile(r"PIKMIN2_LANE\d+_DEEPSEEK_HANDOFF\.md$")
_REGENERATE_COMMAND = "py -3.12 scripts/generate_p2_advance_report.py"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True).stdout


def list_handoffs(branch: str) -> list[str]:
    tree = _git("ls-tree", "-r", "--name-only", branch, "docs/")
    return sorted(name.rsplit("/", 1)[-1] for name in tree.splitlines()
                  if _HANDOFF_RE.search(name))


def read_handoff(branch: str, name: str) -> str:
    return _git("show", f"{branch}:docs/{name}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="claude/p2-deepseek-wave",
                        help="branch whose docs/ carry the lane handoffs")
    parser.add_argument("--output", type=Path, default=None,
                        help="report path (default docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md)")
    args = parser.parse_args(argv)

    names = list_handoffs(args.branch)
    docs = [(name, read_handoff(args.branch, name)) for name in names]
    report = build_advance_report(docs)
    text = render_advance_report(report, _REGENERATE_COMMAND)

    output = args.output or (ROOT / "docs" / "PIKMIN2_ROSTER_ADVANCE_REPORT.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    if args.output is None:
        print(text, end="")
    else:
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
