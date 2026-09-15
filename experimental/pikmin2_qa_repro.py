"""Lane-33 independent QA reproduction (slice 2, #444).

Companion to ``experimental.pikmin2_qa_matrix``. The matrix asserts that a cell
only becomes ``PASS`` on admissible, fully-provenanced evidence; this module
*reproduces* a prior lane's cited run on one integrated build and turns the
reproduction into an evidence record keyed to that build's exe hash. The record
``kind`` defaults to ``fixture`` so a fixture-driven observation never
over-claims natural acceptance; cite ``kind="natural"`` explicitly for a real
run. A lane whose cited ``PASS`` does not reproduce on the integrated build is
reported as a divergence.

``ReproSpec`` is a plain dict with this shape::

    {
        "id": str,                    # unique record id (non-empty)
        "lane": str,                  # source lane label (optional, informational)
        "species": str,               # species under test (optional, informational)
        "stage": str,                 # matrix stage key (see qa_matrix.STAGES)
        "scenario": str,              # matrix scenario key (see qa_matrix.SCENARIOS)
        "natural_markers": [str, ...],# substrings that must all appear in the log
        "exe_sha256": str,            # integrated exe/build hash (becomes build_sha256)
        "root_commit": str,           # pinned source root commit
        "native_commit": str,         # pinned native (bbft) commit
        "kind": str,                  # evidence kind; default "fixture" (see qa_matrix.EVIDENCE_KINDS)
        "accept_exit_codes": [int, ...], # exit codes that count as success; default [0]
        "timed_out_ok": bool,         # True lets a ``timed_out`` run pass when every marker
                                      # is present (timer-terminated non-self-exiting fixtures)
    }

Usage::

    py -3.12 -m experimental.pikmin2_qa_repro emit-record \\
        --spec spec.json --log native.log --exit-code 0 --out record.json \\
        [--note "free-text note"]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experimental import pikmin2_qa_matrix as qa


def _marker_notes(markers, log_text):
    """Human-readable present/absent marker list for the record ``notes``."""
    parts = []
    for marker in markers:
        if marker in log_text:
            parts.append(f"present: {marker}")
        else:
            parts.append(f"absent: {marker}")
    return "; ".join(parts) or "no natural markers"


def reproduce(spec, log_text, exit_code, evidence_paths, timed_out=False, note=""):
    """Replay a ``ReproSpec`` against captured output and return a QA record.

    The record's ``kind`` defaults to ``"fixture"`` so a fixture-driven
    observation never over-claims natural acceptance (pass ``"kind"``
    explicitly for a real run); an unknown kind raises ``ValueError``. Status
    is ``PASS`` only when the process is *accepted* -- ``exit_code`` is in
    ``accept_exit_codes`` (default ``[0]``), or ``timed_out`` is true with
    ``timed_out_ok`` set -- *and* every ``natural_markers`` substring is
    present in ``log_text``; otherwise ``FAIL``. Provenance
    (``root_commit``/``native_commit``/``build_sha256`` and ``evidence_paths``)
    is carried through so the result satisfies
    ``pikmin2_qa_matrix.validate_record``. A non-empty ``note`` is appended to
    the record's ``notes`` (separated from the marker notes by a newline).
    """
    markers = [str(marker) for marker in spec.get("natural_markers") or []]
    present = [marker for marker in markers if marker in log_text]
    absent = [marker for marker in markers if marker not in log_text]
    kind = spec.get("kind") or "fixture"
    if kind not in qa.EVIDENCE_KINDS:
        raise ValueError(f"unknown evidence kind {kind!r}")
    accept_exit_codes = spec.get("accept_exit_codes")
    if accept_exit_codes is None:
        accept_exit_codes = [0]
    accept_exit_codes = list(accept_exit_codes)
    timed_out_ok = bool(spec.get("timed_out_ok", False))
    accepted = (exit_code in accept_exit_codes) or (bool(timed_out) and timed_out_ok)
    passed = accepted and not absent
    notes = _marker_notes(markers, log_text)
    note_text = str(note).strip()
    if note_text:
        notes = f"{notes}\n{note_text}" if notes else note_text
    return {
        "id": spec.get("id"),
        "lane": spec.get("lane"),
        "species": spec.get("species"),
        "stage": spec.get("stage"),
        "scenario": spec.get("scenario"),
        "kind": kind,
        "status": qa.PASS if passed else qa.FAIL,
        "root_commit": spec.get("root_commit", ""),
        "native_commit": spec.get("native_commit", ""),
        "build_sha256": spec.get("exe_sha256", ""),
        "evidence_paths": list(evidence_paths or []),
        "notes": notes,
        "exit_code": exit_code,
        "accept_exit_codes": accept_exit_codes,
        "timed_out": bool(timed_out),
        "checks": {marker: marker in log_text for marker in markers},
        "missing_markers": absent,
    }


def diverge(claimed, observed):
    """Compare a claimed lane record against a ``reproduce`` result.

    ``claimed`` is a prior lane's claimed record (at least ``id``/``lane``/
    ``status``, plus ``notes`` or ``checks``). ``observed`` is the dict returned
    by :func:`reproduce`. A divergence *matters* only when the claimed status is
    ``PASS`` but the observed status is ``FAIL``; the returned
    ``"divergent"`` flag encodes exactly that.
    """
    claimed = claimed or {}
    observed = observed or {}
    claimed_status = claimed.get("status")
    observed_status = observed.get("status")
    checks = observed.get("checks") or {}
    missing = [marker for marker, ok in checks.items() if not ok]
    exe_sha256 = observed.get("build_sha256") or observed.get("exe_sha256") or ""
    lane = observed.get("lane") or claimed.get("lane")
    record_id = observed.get("id") or claimed.get("id")
    divergent = claimed_status == qa.PASS and observed_status == qa.FAIL
    if divergent:
        description = (f"{record_id} (lane {lane}): claimed {claimed_status} but "
                       f"reproduced {observed_status}; {len(missing)} natural "
                       f"markers missing")
    elif claimed_status == qa.PASS and observed_status == qa.PASS:
        description = (f"{record_id} (lane {lane}): claimed and observed PASS "
                       f"agree (no divergence)")
    else:
        description = (f"{record_id} (lane {lane}): claimed {claimed_status}, "
                       f"observed {observed_status}")
    return {
        "id": record_id,
        "lane": lane,
        "claimed_status": claimed_status,
        "observed_status": observed_status,
        "missing_markers": missing,
        "exit_code": observed.get("exit_code"),
        "exe_sha256": exe_sha256,
        "description": description,
        "divergent": divergent,
    }


def report_divergences(specs_and_results):
    """Reduce ``(claimed, observed)`` pairs into divergence reports.

    When a pair carries a claimed status, only *divergent* results (claimed
    ``PASS`` -> observed ``FAIL``) are returned; pairs without a claimed status
    are reported as-is.
    """
    reported = []
    for claimed, observed in specs_and_results:
        divergence = diverge(claimed, observed)
        if (claimed or {}).get("status"):
            if divergence["divergent"]:
                reported.append(divergence)
        else:
            reported.append(divergence)
    return reported


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit-record",
                          help="reproduce a spec against a log and write an evidence record")
    emit.add_argument("--spec", type=Path, required=True,
                      help="JSON file holding a ReproSpec")
    emit.add_argument("--log", type=Path, required=True,
                      help="captured run log text")
    emit.add_argument("--exit-code", type=int, default=0,
                      help="process exit code (default 0)")
    emit.add_argument("--timed-out", action="store_true",
                      help="mark the run timer-terminated (for non-self-exiting fixtures)")
    emit.add_argument("--evidence", action="append", default=[],
                      help="evidence path (repeatable); defaults to the log path")
    emit.add_argument("--note", default="",
                      help="free-text note appended to the record's notes field")
    emit.add_argument("--out", type=Path, required=True,
                      help="output record JSON path")

    args = parser.parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    evidence = args.evidence or [str(args.log)]
    record = reproduce(spec, log_text, args.exit_code, evidence,
                       timed_out=args.timed_out, note=args.note)
    problems = qa.validate_record(record)
    if problems:
        for problem in problems:
            print(f"INVALID {problem}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(f"record id={record['id']} stage={record['stage']} "
          f"scenario={record['scenario']} status={record['status']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
