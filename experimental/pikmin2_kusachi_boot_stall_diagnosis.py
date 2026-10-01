"""Kusachi boot-stall diagnosis analyzer (#822; consumer #818).

Downstream consumer: kusachi-gate-persistence-observation (#818 gen 4).
Read-only analysis of headed boot logs that stall post-audio-init: locates
the stall window between the last observed marker and the first absent
expected marker, cross-checks staged assets, and returns either a pinned
stall window with file:line citations or an exact NEEDS-RUNTIME-PROBE
finding. Fail-closed: malformed logs and missing inputs are refused with a
reason, never defaulted. No runtime, no builds, no launches.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

NATIVE_PIN = "704bad6cff6e1bd1952d72597eba8f76004e400b"

# Ordered boot markers: (marker substring, citation). The stall window is
# reported between the last present marker and the first absent one.
SEQUENCE = [
    ("P2_KUSACHI_CONTENT_WIRING_STAGE",
     "tools/p2_kusachi_content_wiring_fixture.cpp:203 (fixture argv/stage bind)"),
    ("SDL2 Window & OpenGL Context initialized successfully (960x540)",
     "tools/p2_kusachi_content_wiring_fixture.cpp:207-221 (window init)"),
    ("OSInit() - System initialized",
     "src/sysDolphin/system.cpp:1098 (System::Initialise entry)"),
    ("CARDInit() - persistent filesystem card",
     "src/sysDolphin/system.cpp:1099"),
    ("DVDInit() - DVD subsystem initialized",
     "src/sysDolphin/system.cpp:1123"),
    ("[jaudio] NextOS DSP",
     "pc_port/audio/jaudio_sink.cpp:48 (STDERR, unbuffered; via Jac_Start at system.cpp:1160)"),
    ("JAudio wave catalog loaded",
     "pc_port/audio/pc_audio.cpp:693 (first catalog print past the sink open)"),
    ("pikiseq.arc",
     "pc_port/audio/pc_audio.cpp:706 (sequence archive DVD load)"),
    ("PADInit() - SDL2 window",
     "pc_port/dolphin_stubs/pad_stubs.cpp:28 (mControllerMgr.init at system.cpp:1170)"),
    ("P2_CHALLENGE_CONTENT_WIRED",
     "fixture observed loop (wiring truth)"),
]

PINNED = "PINNED"
NEEDS_PROBE = "NEEDS-RUNTIME-PROBE"


class Refused(ValueError):
    """Fail-closed refusal with a reason."""


def read_log_text(path):
    if not os.path.isfile(path):
        raise Refused("boot log missing: " + str(path))
    raw = open(path, "rb").read()
    if not raw.strip():
        raise Refused("boot log is empty: " + str(path))
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise Refused("boot log is not UTF-8 or UTF-16: " + str(path))


def locate_window(text):
    """Split the boot sequence into observed tail and first absence."""
    lines = text.splitlines()
    if not any("P2_KUSACHI_CONTENT_WIRING_STAGE" in l for l in lines):
        raise Refused("not a kusachi wiring boot log (no STAGE marker)")
    present = [marker for marker, _ in SEQUENCE if any(marker in l for l in lines)]
    idx = len(present)
    last = present[-1] if present else None
    first_absent = SEQUENCE[idx][0] if idx < len(SEQUENCE) else None
    return {
        "observed_markers": present,
        "last_observed": last,
        "first_absent": first_absent,
        "complete": first_absent is None,
    }


def check_assets(run_dir):
    """Inventory staged boot assets; missing SndData/stage trees reported."""
    base = os.path.join(run_dir, "assets", "dataDir")
    if not os.path.isdir(base):
        raise Refused("staged assets absent: " + base)
    inv = {}
    for name in ("consFont.bti", "bigFont.bti"):
        p = os.path.join(base, name)
        inv[name] = os.path.isfile(p) and os.path.getsize(p) >= 32
    snd = os.path.join(base, "SndData")
    inv["SndData_tree"] = os.path.isdir(snd)
    stages = os.path.join(base, "stages", "chal0", "default.gen")
    inv["stages/chal0/default.gen"] = os.path.isfile(stages)
    return inv


def analyze(log_path, run_dir=None):
    """Full fail-closed analysis. Returns a verdict dict."""
    text = read_log_text(log_path)
    window = locate_window(text)
    assets = check_assets(run_dir) if run_dir else None
    if window["complete"]:
        return {"verdict": PINNED, "detail": "boot sequence complete",
                "window": window, "assets": assets}
    last, first = window["last_observed"], window["first_absent"]
    if last == "[jaudio] NextOS DSP" and first == "JAudio wave catalog loaded":
        detail = ("stall window: after the DSP sink open "
                  "(jaudio_sink.cpp:48, unbuffered STDERR) and before the "
                  "first catalog print (pc_audio.cpp:693) / SndData DVD "
                  "opens (pc_audio.cpp:706) / PADInit (pad_stubs.cpp:28). "
                  "Caveat: stdout under timeout-kill may under-report; "
                  "the precise intra-init call needs the probe slice.")
        verdict = NEEDS_PROBE if assets is None or not assets.get("SndData_tree") else PINNED
        if assets is not None and not assets.get("SndData_tree"):
            detail += (" Staged SndData tree absent while a healthy JAUDIO "
                       "boot opens SndData in this window: missing-asset "
                       "boot stall is the leading hypothesis.")
    else:
        detail = ("stall between %r and %r; not the catalog window - "
                  "re-audit the sequence" % (last, first))
        verdict = NEEDS_PROBE
    return {"verdict": verdict, "detail": detail, "window": window,
            "assets": assets}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kusachi boot-stall analyzer (#822)")
    ap.add_argument("log", help="boot native.log to analyze")
    ap.add_argument("--run-dir", help="staged run dir for asset inventory")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = analyze(args.log, args.run_dir)
    except Refused as exc:
        print("REFUSED: %s" % exc)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("verdict: %s" % result["verdict"])
        print("detail: %s" % result["detail"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
