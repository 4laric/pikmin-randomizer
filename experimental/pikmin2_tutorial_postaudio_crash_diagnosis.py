"""Tutorial P1 post-audio boot crash diagnosis (issue #750).

Read-only log + code analysis for the deterministic 0xC0000005 crash in the
#148 tutorial P1 staged runs. No engine edits, no runtime launches, no ADMIT.

Proven fault window (both headed logs, byte-identical modulo window
position): the background audio thread prints `[jaudio] NextOS DSP` on a
successful device open, and the process then dies with exit 3221225477
(0xC0000005) before ANY of: a DVDOpen attempt (success or failure), screen-
texture loads, node-manager creation, P2_ROOM_PREVIEW, generator spawns, FPS
lines, or any flushed fixture output (WAIT/observed/markers). The staged
SndData set (48 files incl. Seqs/pikiseq.arc, 219392 bytes) is present, bank
conversion is healthy (18/22 WSYS + 19/22 IBNK, no errors), and the same
partial bank profile survives in other boots -- so audio init, bank loading
and staged-asset resolution are ruled out as the fault.

Ruled out with evidence (see docs/PIKMIN2_TUTORIAL_POSTAUDIO_CRASH_DIAGNOSIS.md):
loader-stage DLL failure (distinguished 0xC0000135 signature with zero
output), audio device open, bank conversion errors, missing staged SndData,
DVD asset resolution of the staged set, font loads (bigFont provably resolves
pre-audio by init order), PADInit (trivially safe), Jac_AddDVDBuffer (proven
side-effect-free for null/empty), p2d_init (null-safe + would DVD-log first),
captain guard (self-test green, no CAPTAIN_DOWN).

Remaining suspects, ranked (hypotheses, NOT proven - a faulting-PC capture
on the pinned exe is required to collapse them):
1. First-frame JAI audio pump (`renderJAudioFrame` in
   pc_port/audio/jaudio_host.cpp, via `DspPlayerCallback` /
   `UpdateDSPchannelAll` / `PlayerCallback` / `StreamMain`) dereferencing a
   null bank/sequel entry.
2. JAI-tail init inside `Jac_Start` (src/jaudio/verysimple.c `Jac_PlayInit`,
   `WaveScene_Set`, `DVDT_CheckPass`, `Jac_Portcmd_Init`, `Jal_CmdQueue_Init`,
   `Jac_InitEventSystem`, `Jac_InitDemoSystem`, `Jac_InitStreamSystem`).
3. Sink-thread teardown race (`serviceSinkOpen` / `joinSinkOpenThread` vs a
   main-thread close) in pc_port/audio/jaudio_host.cpp.
4. gsys tail (`mControllerMgr` beyond init, `mTimer`, cons-font already
   ruled resolvable, `endLoading` thread join) in src/sysDolphin/system.cpp.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

LANE = "tutorial-postaudio-crash-diagnosis"
ISSUE = 750
DOWNSTREAM_LANE = "p2-overworld-tutorial-p1-staged-rerun"
DOWNSTREAM_ISSUE = 148

# Recorded pins (identifiers as reported by the staged-rerun lane).
NATIVE_PIN = "13b4262c78611b6a0279aa65ea5785b614ecd6cf"
ROOT_PIN = "82ba1b8bc82f15b34b623bb3faf0504bdea941d9"
EXE_SHA_PREFIX = "f235e032"
CRASH_EXIT = 3221225477  # 0xC0000005
LOADER_EXIT = 3221225781  # 0xC0000135, distinguished non-crash signature

DSP_MARKER = "[jaudio] NextOS DSP"
BANK_MARKER = "[jaudio-bank] BX ready"


class DiagnosisError(ValueError):
    """A log or pin input violates the diagnosis contract."""


def log_facts(text, exit_code):
    """Extract structured boot facts from a headed-run log (fail-closed)."""
    if not isinstance(text, str) or not text:
        raise DiagnosisError("Log text is missing or empty")
    lines = text.splitlines()
    stripped = [line.strip() for line in lines]
    dvd = [line for line in stripped if "DVDOpen" in line]
    return {
        "lines": len(lines),
        "last_line": stripped[-1] if stripped else "",
        "ends_after_dsp": stripped[-1].startswith("[jaudio] NextOS DSP") if stripped else False,
        "has_bank_ready": any(BANK_MARKER in line for line in stripped),
        "dvd_attempts": len(dvd),
        "dvd_failures": sum("FAILED" in line for line in dvd),
        "has_fps": any("[PC Port] FPS:" in line for line in stripped),
        "has_fixture_markers": any(
            line.startswith(("P2_TUTORIAL_P1_WAIT", "P2_TUTORIAL_P1_ENGINE_FACT",
                             "P2_TUTORIAL_P1_UNSUPPORTED", "FAIL TUTORIAL_P1_RUNTIME"))
            for line in stripped),
        "has_captain_down": any("P2_FIXTURE_CAPTAIN_DOWN" in line for line in stripped),
        "has_room_preview": any("P2_ROOM_PREVIEW" in line for line in stripped),
        "exit_code": exit_code,
    }


def classify_crash(facts):
    """Classify the crash signature from boot facts (fail-closed).

    Returns the fault-window verdict. A log that does not match the exact
    post-audio signature is rejected (no silent misclassification).
    """
    if not isinstance(facts, dict) or not facts:
        raise DiagnosisError("Boot facts missing")
    exit_code = facts.get("exit_code")
    if exit_code == LOADER_EXIT:
        return {"signature": "loader-stage-dll-missing",
                "fault": "process died before any output; missing MinGW runtime DLL, not the engine crash",
                "matches_issue_750": False}
    if exit_code != CRASH_EXIT:
        raise DiagnosisError("Exit code is not the 0xC0000005 crash signature")
    if not facts.get("ends_after_dsp"):
        raise DiagnosisError("Log does not end right after NextOS DSP")
    if not facts.get("has_bank_ready"):
        raise DiagnosisError("Bank-ready line missing; audio init itself failed")
    if facts.get("dvd_attempts"):
        raise DiagnosisError("Post-audio DVD attempts present; different fault phase")
    if facts.get("has_fixture_markers") or facts.get("has_fps"):
        raise DiagnosisError("Engine/fixture markers present; crash is past the audio window")
    return {"signature": "post-audio-pre-file-io-access-violation",
            "fault": "0xC0000005 on the main thread after background sink-open "
                     "success and before any file I/O, flushed fixture output, "
                     "or engine marker",
            "matches_issue_750": True}


def suspects():
    """Ranked suspect phases (hypotheses with file:line, never proven here)."""
    return [
        {"rank": 1,
         "phase": "first-frame JAI audio pump",
         "files": ["pc_port/audio/jaudio_host.cpp:1532 renderJAudioFrame",
                   "pc_port/audio/jaudio_host.cpp:1637 pumpAudio call site"],
         "reason": "only active subsystem in the window with pointer-rich "
                   "state; partial 18/22+19/22 bank loads present"},
        {"rank": 2,
         "phase": "JAI-tail init inside Jac_Start",
         "files": ["src/jaudio/verysimple.c:404 Jac_Start",
                   "src/jaudio/verysimple.c:431 Jac_PlayInit et al."],
         "reason": "unlogged sequel/stream/event/demo init immediately after "
                   "the sink print; no markers on any path"},
        {"rank": 3,
         "phase": "sink-thread teardown race",
         "files": ["pc_port/audio/jaudio_host.cpp:1588 beginSinkOpen",
                   "pc_port/audio/jaudio_host.cpp:1599 serviceSinkOpen"],
         "reason": "background thread owns the sink across the crash window"},
        {"rank": 4,
         "phase": "gsys tail (controller/timers/endLoading)",
         "files": ["src/sysDolphin/system.cpp:1161-1178 System::Initialise tail"],
         "reason": "last unlogged main-thread code before first file I/O; "
                   "individual calls look safe, kept for completeness"},
    ]


def packet(facts, verdict):
    """Build the hashed diagnosis packet naming the downstream consumer."""
    if not verdict.get("matches_issue_750"):
        raise DiagnosisError("Packet requires the issue-750 signature")
    result = {"schema": 1, "lane": LANE, "issue": ISSUE,
              "pins": {"native": NATIVE_PIN, "root": ROOT_PIN,
                       "exe_sha_prefix": EXE_SHA_PREFIX},
              "facts": copy.deepcopy(facts), "verdict": copy.deepcopy(verdict),
              "suspects": suspects(),
              "fix_owner": "engine/audio boot lane via #186 shared review + "
                           "coordinator #570 (no live lane owns it); decisive "
                           "next step is a faulting-PC capture (debugger/crash "
                           "dump) on the pinned exe",
              "downstream": {"lane": DOWNSTREAM_LANE, "issue": DOWNSTREAM_ISSUE,
                             "need": "squad observation once the crash cause "
                                     "is fixed"},
              "gates": "all six UNTESTED", "admit": False}
    result["packet_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()
    return result


def main(argv=None):
    """Analyze a headed-run log file and print the packet as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    text = args.log.read_text(encoding="utf-8", errors="replace")
    facts = log_facts(text, args.exit_code)
    result = packet(facts, classify_crash(facts))
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output is not None:
        if args.output.suffix != ".json":
            raise DiagnosisError("Packet output must be JSON")
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
