"""Generate docs/PIKMIN2_ENEMY_ROSTER.json from the pikmin2 decompilation.

Read-only against the research checkout. Regenerating is deterministic: rerun
after the source revision changes and commit the diff; never hand-edit the JSON.

    py -3.12 scripts/generate_pikmin2_enemy_roster.py
    py -3.12 scripts/generate_pikmin2_enemy_roster.py --source-revision <rev>
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_enemy_roster import (  # noqa: E402
    ROSTER_PATH,
    build_entries,
    entries_from_payload,
    parse_enum_header,
    parse_info_table,
    resolve_ids,
    snapshot_payload,
    summarize,
    validate_roster,
)

DEFAULT_H = "native/pikmin2-research/include/Game/enemyInfo.h"
DEFAULT_CPP = "native/pikmin2-research/src/plugProjectYamashitaU/enemyInfo.cpp"


def detect_revision(checkout: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_payload(h_path: Path, cpp_path: Path, source_revision: str | None) -> tuple[list[dict], dict]:
    enum_records = parse_enum_header(h_path.read_text(encoding="utf-8"))
    table_records = parse_info_table(cpp_path.read_text(encoding="utf-8"))
    entries = resolve_ids(build_entries(enum_records, table_records))
    return entries, snapshot_payload(entries, source_revision)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enemyinfo-h", type=Path, default=ROOT / DEFAULT_H)
    parser.add_argument("--enemyinfo-cpp", type=Path, default=ROOT / DEFAULT_CPP)
    parser.add_argument("--output", type=Path, default=ROSTER_PATH)
    parser.add_argument("--source-revision", default=None)
    args = parser.parse_args()

    revision = args.source_revision or detect_revision(args.enemyinfo_h.parents[3])
    entries, payload = build_payload(args.enemyinfo_h, args.enemyinfo_cpp, revision)
    roster = entries_from_payload(payload)
    validate_roster(roster)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary = summarize(roster)
    print(f"wrote {args.output} ({len(entries)} identities, revision {revision})")
    print("classifications:", summary["classification_counts"])
    print("randomizable candidates:", summary["randomizable_candidates"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
