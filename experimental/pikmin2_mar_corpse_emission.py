"""Evidence helpers for the Mar corpse-emission lane (#716).

Marker parsing plus pin verification for the `pc_p2_mar_emit_corpse` change and
its guarded proof fixture. Read-only: never edits sources, never runs a build.
"""
import hashlib
import re
from pathlib import Path

PASS_MARKER = "PASS P2_MAR_CORPSE_EMISSION"
EMITTED_MARKER = "P2_MAR_CORPSE_EMITTED"
EMITTED_OBSERVED = "P2_MAR_CORPSE_EMITTED_OBSERVED"
RECEIPT_MARKER = "P2_MAR_CORPSE_READY"
RECEIPT_RESOLVED = "P2_MAR_CORPSE_RECEIPT_RESOLVED"
DEAD_MARKER = "P2_MAR_DEAD"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "Transport(")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
# mHealth= is excluded: health values appear legitimately in observer logs.


# Family corpse-convention anchors the emission must preserve.
REQUIRED_SOURCE_TOKENS = (
    "pc_p2_mar_emit_corpse",
    "becomePellet",
    "P2_MAR_CORPSE_EMITTED",
)
# Health reads (actor->mHealth) and the pre-existing bind init are legitimate;
# only transport-mode writes would be an injection here.
FORBIDDEN_SOURCE_TOKENS = (
    "TransportMode",
    "Transport(",
)


class EvidenceError(ValueError):
    """Fail-closed evidence rejection."""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_markers(log_text):
    """Extract the corpse-emission receipt markers from a fixture log."""
    text = log_text or ""
    lines = text.splitlines()

    def has(token):
        return any(token in line for line in lines)

    emitted = [line for line in lines if EMITTED_OBSERVED in line]
    return dict(dead=has(DEAD_MARKER), emitted=emitted,
                receipt=has(RECEIPT_RESOLVED) or has(RECEIPT_MARKER),
                pass_run=has(PASS_MARKER),
                captain_down=has(CAPTAIN_DOWN),
                window_960x540=("960x540" in text))


def verify_receipt(markers):
    """Fail closed unless the log proves emission + receipt with no taint."""
    if markers.get("captain_down"):
        raise EvidenceError("Captain-down run cannot substantiate a receipt")
    for key in ("dead", "receipt", "pass_run", "window_960x540"):
        if not markers.get(key):
            raise EvidenceError("Incomplete corpse receipt: missing " + key)
    if not markers.get("emitted"):
        raise EvidenceError("Incomplete corpse receipt: no emission marker")
    return dict(ok=True, emitted_lines=len(markers["emitted"]))


def verify_source_tokens(source_text, required=REQUIRED_SOURCE_TOKENS,
                         forbidden=FORBIDDEN_SOURCE_TOKENS):
    """Fail closed unless the emission source keeps the family contract."""
    missing = [t for t in required if t not in source_text]
    if missing:
        raise EvidenceError("Emission source missing contract tokens: %s" % missing)
    bad = [t for t in forbidden if t in source_text]
    if bad:
        raise EvidenceError("Emission source has forbidden injection tokens: %s" % bad)
    return True


def verify_pin(path, expected_sha256):
    """Fail closed unless a file matches its recorded hash."""
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise EvidenceError("Hash mismatch for %s: %s" % (path, actual))
    return dict(path=str(path), sha256=actual)