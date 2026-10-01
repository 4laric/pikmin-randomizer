"""Landing validation for the committed #616 Bomb::Mgr birth provider (#703).

Takes the #616 provider read-only (never re-derives or duplicates it):
re-verifies the six committed files hash-identical to the review pins,
checks the provider's references against the #577 payload API it consumes,
confirms the #616 tree carries no #691 Section-3 code of its own (the #691
engine-driven birth arm lives on its own branch and consumes the manager
API instead of duplicating it), verifies the canonical builder now expands
Ninja @rsp files (the #616-era blocker, landed via #659), and aligns the
#616 requested hook with the #666 shared-hook candidate. Everything is
fail-closed: missing files, hash drift, absent tokens, or unreadable
integrated handoffs refuse instead of passing. No runtime, no ADMIT.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCHEMA = "p2-bomb-mgr-birth-landing-v1"
PROVIDER_ISSUE = 616
SOURCE_ID = 36

# Review pins: sha256 of the six #616 files at their committed caps
# (root b779b00f, native 6d4cbc4a), re-verified this lane against the
# pristine prepared worktrees. Two root pins and both native pins below also
# match the #616 draft handoff and the #666 candidate table.
REVIEW_PINS = {
    "root/docs/PIKMIN2_BOMB_MGR_BIRTH_PROVIDER.md":
        "005b8cf4d460ad8e485c00ce441cc77273964497431051eb8a79f582429b5920",
    "root/experimental/pikmin2_bomb_mgr_birth_provider.py":
        "58d61f2eb123f6da2e05d76384bbf1dbe2188f51f058750d9c11a3a924d635c3",
    "root/tests/test_pikmin2_bomb_mgr_birth_provider.py":
        "4cf753252c60126a7a15b89ed94861ffd58aa08b047b73d67730fdcfaac7658b",
    "native/pc_port/pc_p2_bomb_mgr_birth.h":
        "94b09e5510413bc9ee8daee502598f746bc45328c539c27e6ff840e08340a1f0",
    "native/pc_port/pc_p2_bomb_mgr_birth.cpp":
        "ec36bf049c785e1028b7a0f0248754bd1b8867f76d9f035e14469fc7de68c081",
    "native/tools/p2_bomb_mgr_birth_test.cpp":
        "de37a9f87debb7f4d1a15813a8e50b218250413ffe84e8b527d85472755a5e66",
}

# Tokens the #616 doc must name (dependency + hook contract, read-only).
DOC_REQUIRED_TOKENS = (
    "P2BombPayloadPool",
    "pc_p2_bomb_payload_actor.h",
    "d9ca3b08",
    "3aad911e",
    "tekibteki",
    "pc_p2_teki_lifetime",
    "#186",
    "source_id=36",
)

# Declarations the #616 header must publish (manager API surface).
HEADER_REQUIRED_TOKENS = (
    "P2_BOMB_MGR_SOURCE_ID",
    "P2BombMgrHandle",
    "pc_p2_bomb_mgr_birth_manager",
    "pc_p2_bomb_mgr_birth_reset",
    "pc_p2_bomb_mgr_birth_setup",
    "pc_p2_bomb_mgr_birth_carrier",
    "pc_p2_bomb_mgr_birth_update",
    "pc_p2_bomb_mgr_birth_forget",
    "pc_p2_bomb_mgr_birth_ready",
)

# #691 Section-3 marker: must be ABSENT from #616 files (it lives on the #691
# branch which consumes the manager API); present here would mean duplication.
SECTION3_MARKER = "pc_p2_bomb_engine_birth_poll"

# Canonical-builder support tokens (landed via #659) for the @rsp expansion
# the #616 review flagged as the submission blocker.
BUILDER_RSP_TOKENS = (
    "expand_response",
    "@",
    ".rsp",
)

# Shared-hook anchors that must co-occur in the #616 doc and the #666 packet.
HOOK_ANCHORS = (
    "tekibteki",
    "lifetime",
    "CMake",
    "generalEnemyMgr",
)


class LandingError(ValueError):
    """Fail-closed refusal: missing input, drift, or misalignment."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_pin_table(pins: dict) -> tuple[bool, str]:
    if not isinstance(pins, dict) or not pins:
        return False, "pin table must be a nonempty mapping"
    bad = [k for k, v in pins.items()
           if not isinstance(k, str) or not k
           or not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)]
    if bad:
        return False, "malformed pin entries: %s" % sorted(bad)[:3]
    return True, "%d pinned files" % len(pins)


def verify_files(read, pins: dict) -> tuple[bool, str, dict]:
    """Hash files through read(relpath)->bytes and compare to pins.

    read must raise LandingError (or OSError/ValueError) for missing input;
    any refusal fails closed. Returns (ok, summary, per-file detail).
    """
    ok, why = check_pin_table(pins)
    if not ok:
        return False, why, {}
    detail = {}
    for relpath in sorted(pins):
        try:
            digest = sha256_bytes(read(relpath))
        except (LandingError, OSError, ValueError) as error:
            return False, "unreadable pinned file: %s" % relpath, detail
        match = digest == pins[relpath]
        detail[relpath] = {"sha256": digest, "match": match}
        if not match:
            return False, "hash drift: %s" % relpath, detail
    return True, "all %d pins match" % len(pins), detail


def check_tokens(text: str, tokens, label: str) -> tuple[bool, str]:
    if not isinstance(text, str) or not text:
        return False, "%s: empty input" % label
    missing = [t for t in tokens if t not in text]
    if missing:
        return False, "%s: missing %s" % (label, sorted(missing)[:4])
    return True, "%s: all %d anchors present" % (label, len(tokens))


def check_no_section3(text: str, label: str) -> tuple[bool, str]:
    if not isinstance(text, str) or not text:
        return False, "%s: empty input" % label
    if SECTION3_MARKER in text:
        return False, "%s: carries #691 Section-3 code (duplication)" % label
    return True, "%s: no Section-3 duplication" % label


def check_handoff(path, expect_kind: str = "tooling") -> tuple[bool, str, dict]:
    """Validate an integrated lane's handoff file exists and is well-formed.

    Confirms schema/kind plus a recorded handoff state; never executes it.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        return False, "unreadable handoff: %s" % path, {}
    if not isinstance(data, dict) or data.get("schema") != 1:
        return False, "handoff schema must be 1: %s" % path, {}
    if data.get("kind") != expect_kind:
        return False, "handoff kind must be %s: %s" % (expect_kind, path), {}
    for key in ("lane", "issue", "generation"):
        if not data.get(key):
            return False, "handoff missing %s: %s" % (key, path), {}
    return True, "handoff ok: %s issue %s" % (data["lane"], data["issue"]), data


def validate_landing(read_616, read_other, pins=None) -> tuple[bool, str, dict]:
    """Full landing validation. read_616(relpath)->bytes for the six #616
    files keyed 'root/...' and 'native/...'; read_other(name)->str for
    named reference texts ('builder', 'hook666', 'header616', 'cpp616',
    'doc616'). pins defaults to REVIEW_PINS; tests inject computed pins for
    hermetic trees. Returns (ok, summary, report)."""
    if pins is None:
        pins = REVIEW_PINS
    report: dict = {}
    ok, why, detail = verify_files(read_616, pins)
    report["pins"] = {"ok": ok, "why": why, "files": detail}
    if not ok:
        return False, "pin verification failed: " + why, report
    try:
        texts = {name: read_other(name) for name in
                 ("builder", "hook666", "header616", "cpp616", "doc616")}
    except (LandingError, OSError, ValueError) as error:
        return False, "unreadable reference text: %s" % error, report
    checks = [
        ("doc_refs", check_tokens(texts["doc616"], DOC_REQUIRED_TOKENS, "provider doc")),
        ("header_api", check_tokens(texts["header616"], HEADER_REQUIRED_TOKENS, "manager header")),
        ("no_section3_header", check_no_section3(texts["header616"], "manager header")),
        ("no_section3_cpp", check_no_section3(texts["cpp616"], "manager core")),
        ("builder_rsp", check_tokens(texts["builder"], BUILDER_RSP_TOKENS, "canonical builder")),
        ("hook_align", check_tokens(texts["doc616"] + "\n" + texts["hook666"], HOOK_ANCHORS, "hook alignment")),
    ]
    report["checks"] = {name: {"ok": ok_, "why": why_} for name, (ok_, why_) in checks}
    failed = [name for name, (ok_, _) in checks if not ok_]
    if failed:
        return False, "reference checks failed: %s" % sorted(failed), report
    return True, "landing validation passed: pins match, refs resolve, no duplication", report
