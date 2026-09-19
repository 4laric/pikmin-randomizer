"""Rover spawn-count reconciliation checker (issue #699).

Read-only analysis of a staged cave-entry run directory against engine
spawn/checkpoint semantics. Given a staged p2-cave-entry.txt (or its absence),
the staged default.gen size, and the run native.log, it reports which side of
the checkpoint failed:

- entry-missing: no p2-cave-entry.txt staged, so pc_p2_cave_setup returns
  silently and no RESTORE/GENERATE markers can appear;
- staging-path: the engine opened a different default.gen than the staged one
  (overlay ineffective), so the staged Pikmin never spawn and the live count
  cannot match the entry;
- count-or-timing: same gen opened but the spawn-count validation still
  aborted, so the live-vs-staged count or the spawn timing is at fault;
- consistent: entry count, opened gen, RESTORE lines and GENERATE markers all
  agree (the checkpoint would pass).

Fail-closed: captain-down evidence, injected markers, malformed entries or
missing legs yield refused/blocked verdicts, never a pass. Emits no markers
and claims no runtime; all six gates stay UNTESTED by this review.
"""
import argparse
import json
import re
import sys

RESTORE_RE = re.compile(r"^P2_CAVE_RESTORE species=(\d+) maturity=(\d+)", re.MULTILINE)
GENERATE_RE = re.compile(r"P2_CAVE_GENERATE_")
FPS_RE = re.compile(r"\[PC Port\] FPS:")
ROOM_READY_RE = re.compile(r"P2_ROOM_READY")
CAVE_READY_RE = re.compile(r"P2_CAVE_READY floor=(\d+) survivors=(\d+)")
ABORT_RE = re.compile(r"Invalid P2 cave entry: spawn count differs from checkpoint")
OPENED_GEN_RE = re.compile(r'DVDOpen\("dataDir/stages/chal0/default\.gen"\) -> OK, size = (\d+)')

_CAPTAIN_DOWN_TOKENS = (
    "P2_FIXTURE_CAPTAIN_DOWN",
    "GAMEEND_",
)

_INJECTED_TOKENS = ("P2_MUSE_DAMAGUMO_INJECT", "mHealth=", "health=99999")


def parse_entry(text):
    """Parse a staged p2-cave-entry.txt; None when absent, refused when bad."""
    if text is None:
        return None
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {"malformed": True}
    head = lines[0].split()
    if len(head) != 5 or head[0] != "P2_CAVE_ENTRY_1":
        return {"malformed": True}
    try:
        count = int(head[4])
    except ValueError:
        return {"malformed": True}
    pairs = lines[1:]
    if len(pairs) != count:
        return {"malformed": True, "count": count, "pairs": len(pairs)}
    return {"malformed": False, "version": head[0], "token": head[1],
            "floor": head[2], "health": head[3], "count": count,
            "pairs": len(pairs)}


def parse_log(text):
    text = text or ""
    return {
        "restores": len(RESTORE_RE.findall(text)),
        "generates": len(GENERATE_RE.findall(text)),
        "fps": len(FPS_RE.findall(text)),
        "room_ready": bool(ROOM_READY_RE.search(text)),
        "cave_ready": bool(CAVE_READY_RE.search(text)),
        "abort_spawn_mismatch": bool(ABORT_RE.search(text)),
        "opened_gen_sizes": [int(m.group(1)) for m in OPENED_GEN_RE.finditer(text)],
        "captain_down": any(t in text for t in _CAPTAIN_DOWN_TOKENS),
        "injected": any(t in text for t in _INJECTED_TOKENS),
    }


def reconcile(entry_text, log_text, staged_gen_size=None, expect_restores=60):
    log = parse_log(log_text)
    if log["captain_down"]:
        return {"verdict": "blocked", "reason": "captain-down",
                "detail": "Captain-down evidence; cannot substantiate any count claim.",
                "log": log, "entry": None}
    if log["injected"]:
        return {"verdict": "refused:injected", "reason": "injected",
                "detail": "Injected markers present; refusing analysis.",
                "log": log, "entry": None}
    entry = parse_entry(entry_text)
    if entry is None:
        return {"verdict": "entry-missing", "reason": "staging",
                "detail": ("No p2-cave-entry.txt staged: pc_p2_cave_setup returns "
                           "silently, so 0 RESTORE/0 GENERATE markers are expected and "
                           "the restore-count checkpoint cannot pass. Correction: "
                           "restore the entry file into the run dir."),
                "log": log, "entry": None}
    if entry.get("malformed"):
        return {"verdict": "refused:malformed-entry", "reason": "staging",
                "detail": "Staged entry is malformed; refusing analysis.",
                "log": log, "entry": entry}
    if log["abort_spawn_mismatch"]:
        opened = log["opened_gen_sizes"]
        if staged_gen_size is not None and opened and all(s != staged_gen_size for s in opened):
            return {"verdict": "staging-path", "reason": "staging",
                    "detail": ("Engine opened default.gen size %s, not the staged %s: "
                               "the arena overlay is ineffective in this boot path, so the "
                               "staged Pikmin never spawn and the live count cannot match "
                               "the entry count %d. Correction: stage the run so the engine "
                               "loads the staged gen (opened size must equal staged size) "
                               "and keep the entry file." % (
                                   opened, staged_gen_size, entry["count"])),
                    "log": log, "entry": entry}
        return {"verdict": "count-or-timing", "reason": "needs-measurement",
                "detail": ("Same gen opened but the spawn-count validation still aborted: "
                           "measure the live pikiMgr count at setup time to separate a "
                           "wrong staged count from spawn timing."),
                "log": log, "entry": entry}
    if (log["restores"] == entry["count"] and log["restores"] >= expect_restores
            and log["generates"] > 0 and log["cave_ready"]):
        return {"verdict": "consistent", "reason": "none",
                "detail": ("Entry count, RESTORE lines and GENERATE markers agree; "
                           "the checkpoint would pass."),
                "log": log, "entry": entry}
    return {"verdict": "incomplete", "reason": "unobserved",
            "detail": ("Boot did not reach the restore checkpoint "
                       "(restores=%d/%d, generates=%d, cave_ready=%s). No fault "
                       "assigned." % (log["restores"], entry["count"],
                                      log["generates"], log["cave_ready"])),
            "log": log, "entry": entry}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", help="Staged p2-cave-entry.txt (omit when absent)")
    parser.add_argument("--log", required=True, help="Run native.log path")
    parser.add_argument("--staged-gen-size", type=int, default=None)
    parser.add_argument("--expect-restores", type=int, default=60)
    args = parser.parse_args(argv)
    entry_text = (open(args.entry, encoding="utf-8", errors="replace").read()
                  if args.entry else None)
    log_text = open(args.log, encoding="utf-8", errors="replace").read()
    print(json.dumps(reconcile(entry_text, log_text, args.staged_gen_size,
                               args.expect_restores), indent=1))


if __name__ == "__main__":
    main()

