"""P1 private runtime import for the shared overworld course boot flag (issue #767).

Provides a dependency-free course-record validator plus run-log reader for
the game-linked guarded fixture (native/tools/p2_overworld_boot_flag_fixture.cpp).
The fixture proves the new additive module (native/pc_port/pc_p2_overworld_course.*):
argv selection of one of the four overworld courses, registration, headed
boot with observed guarded ticks. Captain safety #632 is mandatory for any
runtime run executed from this lane. All six gates stay UNTESTED unless
genuinely observed; no playability claim beyond observed evidence; no ADMIT,
no ledger writes. pc_bbft.cpp/.h and CMakeLists.txt are NEVER edited here;
their argv wiring is the serialized follow-on after staged scope
challenge-pc-bbft-followon #755 via #186 review + integrator.
"""
from __future__ import annotations

from pathlib import Path

COURSES = ("tutorial", "forest", "yakushima", "last")

GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

WINDOW_MARKER = "P2_OVERWORLD_BOOT_FLAG_WINDOW width=960 height=540 centred=1"
REGISTERED_MARKER = "P2_OVERWORLD_COURSE_REGISTERED"
OBSERVED_PREFIX = "P2_OVERWORLD_COURSE_OBSERVED course="
STAGE_PASS_MARKER = "PASS OVERWORLD_BOOT_FLAG"


class BootFlagError(ValueError):
    """Fail-closed boot-flag rejection."""


def validate_course_record(record):
    """Validate a course record dict against the four known courses."""
    if not isinstance(record, dict):
        raise BootFlagError("course record must be a dict")
    course = record.get("course_id")
    if course not in COURSES:
        raise BootFlagError("unknown course_id: %r" % (course,))
    if record.get("index") != COURSES.index(course):
        raise BootFlagError("index mismatch for %r" % (course,))
    return dict(record)


def default_record(course_id="last"):
    """Catalogued course record skeleton (no source bytes claimed)."""
    if course_id not in COURSES:
        raise BootFlagError("unknown course_id: %r" % (course_id,))
    return {"course_id": course_id, "index": COURSES.index(course_id)}


def read_run_log_file(path):
    """Read a native run log from disk (utf-8 or utf-16) as text."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-8"):
        try:
            return raw.decode(encoding).replace(chr(0), "")
        except (UnicodeDecodeError, ValueError):
            continue
    raise BootFlagError("run log is not decodable text: %s" % (path,))


def _flag_line(text, course):
    return "P2_OVERWORLD_COURSE_FLAG course=%s index=%d" % (course, COURSES.index(course))


def evaluate_gates(text, exit_code=None):
    """Map observed markers to honest gate rows.

    PASS only on an observed marker; BLOCKED only on an observed
    CAPTAIN_DOWN line or a nonzero exit; anything else UNTESTED.
    """
    if not isinstance(text, str):
        raise BootFlagError("run log must be text")
    window = WINDOW_MARKER in text
    down = "P2_FIXTURE_CAPTAIN_DOWN" in text
    flagged = [_flag_line(text, c) in text for c in COURSES]
    flag = any(flagged)
    course = COURSES[flagged.index(True)] if flag else None
    registered = REGISTERED_MARKER in text and flag
    observed = OBSERVED_PREFIX in text and flag
    stage_pass = STAGE_PASS_MARKER in text and flag
    if window and not down:
        guard = ("PASS", "guard silent during observed run")
    elif down:
        guard = ("BLOCKED", "P2_FIXTURE_CAPTAIN_DOWN observed")
    else:
        guard = ("UNTESTED", "no run observed")
    if stage_pass and exit_code == 0:
        done = ("PASS", "exit 0 with stage PASS")
    elif down or (exit_code is not None and exit_code != 0):
        qualifier = "CAPTAIN_DOWN marker" if down else "nonzero exit"
        done = ("BLOCKED", "exit %r with %s" % (exit_code, qualifier))
    elif exit_code is None:
        done = ("UNTESTED", "exit code not recorded")
    else:
        done = ("UNTESTED", "exit %r without markers" % (exit_code,))
    return [
        {"token": "window-960x540-centred", "status": "PASS" if window else "UNTESTED",
         "evidence": WINDOW_MARKER if window else "no window marker"},
        {"token": "captain-guard-silent", "status": guard[0], "evidence": guard[1]},
        {"token": "course-flag",
         "status": "PASS" if flag else "UNTESTED",
         "evidence": (_flag_line(text, course) if flag else "no course flag marker")},
        {"token": "course-registered",
         "status": "PASS" if registered else "UNTESTED",
         "evidence": REGISTERED_MARKER if registered else "no registration marker"},
        {"token": "guarded-observation",
         "status": "PASS" if observed else "UNTESTED",
         "evidence": OBSERVED_PREFIX.rstrip(" course=") if observed else "no observation marker"},
        {"token": "exit-status", "status": done[0], "evidence": done[1]},
    ]
