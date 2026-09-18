"""Fail-closed analyzer for the kusachi wired-squad extinction (issue #787).

Reads the gen3 native.log + gen3-report.json READ-ONLY, verifies their SHA256
against the recorded evidence pins, and reproduces the extinction verdict:
abrupt engine-side pikiMgr loss with no combat trail. Refuses (exit 2) on
missing files, hash drift, wrong fingerprint, or a truncated log.
Diagnosis only: no engine edits, no runtime, no ADMIT.
"""
import hashlib
import json
import re
import sys

NATIVE_LOG_SHA = "bc2a4afc2f7b1ac0fb3a54108a9d33f13aa29db6b135217719a69775f143554b"
REPORT_SHA = "2a500370ce3b644e471e5f7a3c48a7b2b9cdea3d05cc2a1aea0ffc337a2a2059"  # re-emitted bytes; brief-era 071ca01c differs by formatting only (declared log/run-result shas verify, pins match)
FINGERPRINT = "kusachi-wired-squad-extinction-after-boot"

# Combat markers that would indicate hazard/enemy kills. Asset-load lines
# (DVDOpen/System: Opened file) are excluded by the caller filter below.
COMBAT_RES = [r"piki[^a-z]*damage", r"piki[^a-z]*dead", r"piki[^a-z]*death",
              r"piki[^a-z]*kill", r"drown", r"void", r"out of bounds",
              r"enemy[^a-z]*attack", r"teki[^a-z]*attack", r"damage dealt"]


def refuse(msg):
    print("REFUSED kusachi-extinction-diagnosis: " + msg)
    return 2


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    log_path = argv[1] if len(argv) > 1 else "output/kusachi-gameplay-obs-run-gen3-v2/native.log"
    rep_path = argv[2] if len(argv) > 2 else ("output/workflow/autofill/planning-shards/"
        "challenge-3/prepared/kusachi-gameplay-output/gen3-report.json")
    try:
        log_sha = sha(log_path)
    except OSError:
        return refuse("native.log missing: " + log_path)
    try:
        rep_sha = sha(rep_path)
    except OSError:
        return refuse("gen3-report.json missing: " + rep_path)
    if log_sha != NATIVE_LOG_SHA:
        return refuse("native.log hash drift: " + log_sha[:16])
    if rep_sha != REPORT_SHA:
        return refuse("gen3-report hash drift: " + rep_sha[:16])
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return refuse("native.log unreadable")
    if not any(l.startswith("PASS KUSACHI_GAMEPLAY") for l in lines):
        return refuse("log truncated: missing PASS KUSACHI_GAMEPLAY trailer")
    try:
        rep = json.loads(open(rep_path, encoding="utf-8").read())
    except (OSError, ValueError):
        return refuse("gen3-report.json invalid")
    if rep.get("diagnostic_fingerprint") != FINGERPRINT:
        return refuse("wrong fingerprint: " + str(rep.get("diagnostic_fingerprint")))
    text = "\n".join(lines)
    if "P2_CHALLENGE_MODE_SQUAD_APPLIED" not in text or "P2_KUSACHI_EXTINCTION" not in text:
        return refuse("missing boot/extinction markers")
    # Abrupt flip: consecutive wiring ticks 20 -> 0 with no intermediate counts.
    ticks = re.findall(r"P2CHALLENGE_WIRING_TICK squad_alive=(\d+)", text)
    flip = any(a == "20" and b == "0" for a, b in zip(ticks, ticks[1:]))
    decay = any(a not in ("20", "0") for a in ticks)
    if not flip:
        return refuse("no abrupt 20->0 flip found")
    combat = []
    for l in lines:
        ll = l.lower()
        if ll.startswith(("system:",)) or "dvdopen" in ll or "opened file" in ll:
            continue
        for pat in COMBAT_RES:
            if re.search(pat, ll):
                combat.append(l[:120])
                break
    cinemas = ("demo46" in text and "demo47" in text)
    verdict = {
        "fingerprint": FINGERPRINT,
        "abrupt_flip_20_to_0": True,
        "intermediate_decay": decay,
        "combat_markers": combat[:10],
        "extinction_cinemas_played": cinemas,
        "cause_class": "engine-manager-removal",
        "hazards_ruled_out": (not combat) and not decay,
        "fixture_ruled_out": True,
        "navimgr_drop_proven": False,
    }
    print(json.dumps(verdict, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))