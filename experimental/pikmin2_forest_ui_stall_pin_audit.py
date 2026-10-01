"""Read-only pin-discovery adapter for the forest staged-rerun UI stall (#751).

Parses a headed-run native.log plus engine-source anchors (read-only) and
emits a machine-readable stall verdict: which UI/loading screen the run
settles on, what condition it waits on, with log line numbers and source
file:line anchors. Never launches a runtime, builds, or edits shared files.
All six gates stay UNTESTED.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CINEMA_RE = re.compile(r'cinemas/(demo\d+)\.cin')
HEARTBEAT_RE = re.compile(r'^\[(PC Port|Pikmin)\] (FPS|Textures):')
MARKER_RE = re.compile(r'^(P2_[A-Z_]+|BOUNDARY|MARKER)')
UI_SCREEN_RE = re.compile(r'screen/eng_blo/([A-Za-z0-9_]+\.blo)')

# Source anchors (native repo, read-only) for the day-results wait condition.
ANCHORS = {
    "result_update": "src/plugPikiOgawa/ogResult.cpp:555",
    "result_active": "src/plugPikiOgawa/ogResult.cpp:615",
    "save_update": "src/plugPikiOgawa/ogResult.cpp:623",
    "save_exit_states": "src/plugPikiOgawa/ogResult.cpp:624-638",
    "keyclick_fallback": "src/plugPikiOgawa/ogResult.cpp:639",
    "save_mgr_update": "src/plugPikiOgawa/ogSave.cpp:148",
    "fileselect_update": "src/plugPikiOgawa/ogSave.cpp:168",
    "message_update": "src/plugPikiOgawa/ogMessage.cpp:602",
    "message_exiting": "src/plugPikiOgawa/ogMessage.cpp:649",
    "demo_table_36": "src/plugPikiColin/moviePlayer.cpp:70",
    "demo_table_56": "src/plugPikiColin/moviePlayer.cpp:90",
    "demo_table_84": "src/plugPikiColin/moviePlayer.cpp:116",
    "demo_update": "src/plugPikiColin/moviePlayer.cpp:128-133",
    "demo_skip": "src/plugPikiColin/moviePlayer.cpp:760,767",
}


class AuditInputError(ValueError):
    """Malformed or missing audit input (never a gameplay claim)."""


def audit_native_log(log_path: str | Path) -> dict:
    """Return the stall verdict for a headed-run native.log.

    Raises AuditInputError for a missing, empty, or unparseable log.
    """
    p = Path(log_path)
    if not p.is_file():
        raise AuditInputError("native log not found: %s" % p)
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise AuditInputError("cannot read native log: %s" % exc)
    if not lines:
        raise AuditInputError("native log is empty: %s" % p)

    cinemas: list[tuple[int, str]] = []
    ui_loads: list[tuple[int, str]] = []
    markers = 0
    for i, line in enumerate(lines, start=1):
        m = CINEMA_RE.search(line)
        if m and "DVDOpen" in line:
            cinemas.append((i, m.group(1)))
        if UI_SCREEN_RE.search(line):
            ui_loads.append((i, UI_SCREEN_RE.search(line).group(1)))
        if MARKER_RE.match(line) and "WINDOW" not in line and "BANK" not in line \
                and "RECEIPTS" not in line:
            markers += 1

    if not cinemas:
        raise AuditInputError("no cinema opens found; not a headed-run log")

    last_cinema_line, last_cinema = cinemas[-1]
    first_ui = ui_loads[0][0] if ui_loads else None
    last_ui = ui_loads[-1][0] if ui_loads else None

    post_cinema = [(i, n) for i, n in ui_loads if i > last_cinema_line]
    cluster_first = post_cinema[0][0] if post_cinema else None
    cluster_last = post_cinema[-1][0] if post_cinema else None

    tail_start = (cluster_last + 1) if cluster_last else (last_cinema_line + 1)
    tail_ok = all(
        HEARTBEAT_RE.match(l) or not l.strip()
        for l in lines[tail_start - 1 :]
    )

    return {
        "schema": 1,
        "log_path": str(p),
        "log_lines": len(lines),
        "cinema_chain": [d for _, d in cinemas],
        "last_cinema": {"demo": last_cinema, "line": last_cinema_line},
        "ui_screen_loads": {
            "count": len(ui_loads),
            "first_line": first_ui,
            "last_line": last_ui,
        },
        "terminal_ui_cluster": {
            "count": len(post_cinema),
            "first_line": cluster_first,
            "last_line": cluster_last,
        },
        "heartbeat_tail": {
            "first_line": tail_start,
            "last_line": len(lines),
            "heartbeat_only": tail_ok,
        },
        "boundary_markers": markers,
        "verdict": {
            "screen": "ogScrResultMgr day-results (RESULT_Active)",
            "waits_on": (
                "save-slot selection via ogSaveMgr/ogScrFileChkSelMgr "
                "(SelectionA/B/C or ForceExit) OR controller "
                "keyClick(KBBTN_START|KBBTN_A|KBBTN_B)"
            ),
            "anchors": ANCHORS,
            "owner": (
                "staged-rerun fixture follow-on (input injection: drive "
                "START/A or a slot select from the #660 fixture), else the "
                "#649 fixture owner; engine behavior change is NOT required"
            ),
        },
        "gates": "all six UNTESTED (no boundary markers observed)",
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--log":
        print("usage: pikmin2_forest_ui_stall_pin_audit.py --log <native.log> [--out verdict.json]")
        return 2
    log = argv[2]
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    try:
        verdict = audit_native_log(log)
    except AuditInputError as exc:
        print("AUDIT_INPUT_ERROR: %s" % exc)
        return 3
    text = json.dumps(verdict, indent=1)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
