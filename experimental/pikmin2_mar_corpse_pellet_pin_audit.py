"""Mar corpse-pellet pin audit (issue #799). Audits a staged arena pelletsbin.dir plus a fixture run log. Markers: P2_MAR_PELLET_ENTRY, P2_MAR_PELLET_ABSENT, P2_MAR_PELLET_REFUSED, P2_MAR_PELLET_VERDICT, P2_MAR_RUNLOG. Exit 0 audited, 2 refused. Read-only; stdlib only."""
import os
import re
import sys

ENTRY_RE = re.compile(rb"[ -~]{4,64}\.bin")
BIND_RE = re.compile(r"P2_MAR_DEAD generator=(\d+)")
CORPSE_WAIT_RE = re.compile(r"P2_MAR_CORPSE_WAIT tick=\d+ corpse=(\d+)")

def read_entries(dir_path):
    with open(dir_path, "rb") as fh:
        blob = fh.read()
    if len(blob) < 8:
        return None
    names = sorted(set(m.group(0).decode("ascii") for m in ENTRY_RE.finditer(blob)))
    return names

def audit(arena_dir, log_path):
    markers = []
    pdir = os.path.join(arena_dir, "assets", "dataDir", "archives", "pelletsbin.dir")
    if not os.path.isdir(arena_dir):
        return markers, "missing-arena-dir"
    if not os.path.isfile(pdir):
        return markers, "missing-pelletsbin-dir"
    try:
        names = read_entries(pdir)
    except OSError:
        return markers, "unreadable-pelletsbin-dir"
    if names is None:
        return markers, "malformed-pelletsbin-dir"
    enemy_entries = [n for n in names if not os.path.basename(n).startswith("white")]
    for n in names:
        markers.append("P2_MAR_PELLET_ENTRY %s" % n)
    if not enemy_entries:
        markers.append("P2_MAR_PELLET_ABSENT enemy-corpse")
    if log_path is not None:
        if not os.path.isfile(log_path):
            return markers, "missing-run-log"
        try:
            with open(log_path, "r", encoding="utf-8", errors="strict") as fh:
                text = fh.read()
        except (OSError, UnicodeError):
            return markers, "unreadable-run-log"
        seen = set()
        if BIND_RE.search(text):
            seen.add("BIND")
            markers.append("P2_MAR_RUNLOG BIND")
        if "P2_MAR_CORPSE_OBSERVED_DEAD" in text:
            seen.add("DEAD")
            markers.append("P2_MAR_RUNLOG DEAD")
        m = CORPSE_WAIT_RE.search(text)
        if m and m.group(1) != "0":
            seen.add("CORPSE")
            markers.append("P2_MAR_RUNLOG CORPSE")
        if not seen:
            markers.append("P2_MAR_RUNLOG NONE")
    verdict = "entries-present" if enemy_entries else "absence-verified"
    markers.append("P2_MAR_PELLET_VERDICT %s" % verdict)
    return markers, None

def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        print("P2_MAR_PELLET_REFUSED reason=usage")
        return 2
    log = argv[2] if len(argv) > 2 else None
    markers, refused = audit(argv[1], log)
    for m in markers:
        print(m)
    if refused is not None:
        print("P2_MAR_PELLET_REFUSED reason=%s" % refused)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
