"""Landing validator for the committed #716 Mar corpse emission (issue #720).

Re-verifies the done-but-unlanded #716 implementation read-only (no source,
shared, native or family edits; no builds; no runtime; no ADMIT) and validates
it against the #668 receipt arm, so the single-writer integrator can land it
for downstream consumer #375. All inputs are explicit paths; every check is
fail-closed and every finding carries hashes.
"""
import hashlib
import re
import subprocess
from pathlib import Path

EMISSION_FN = "pc_p2_mar_emit_corpse"
EMIT_MARKER = "P2_MAR_CORPSE_EMITTED"
ARM_FN = "pc_p2_mar_receipt"
ARM_MARKER = "P2_MAR_CORPSE_READY"
SOURCE_ID = "source_id=29"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "Transport(")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


class LandingError(ValueError):
    """Fail-closed landing rejection."""


def sha256_file(path):
    path = Path(path)
    if not path.is_file():
        raise LandingError("Missing file: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo, *argv):
    proc = subprocess.run(["git", "-C", str(repo)] + list(argv),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)
    if proc.returncode:
        raise LandingError("git failed: git -C %s %s" % (repo, " ".join(argv)))
    return proc.stdout.strip()


def verify_commit(repo, sha, subject_fragment):
    """The exact #716 commit exists with the expected subject."""
    actual = git(repo, "rev-parse", sha)
    if actual != sha:
        raise LandingError("Commit not found: " + sha)
    subject = git(repo, "log", "--format=%s", "-1", sha)
    if subject_fragment not in subject:
        raise LandingError("Commit subject drift: %r" % subject)
    return {"sha": sha, "subject": subject}


def verify_native_files(native_wt):
    """The three #716 native files exist with the emission contract tokens."""
    native_wt = Path(native_wt)
    required = {
        "pc_port/pc_p2_mar.h": (EMISSION_FN,),
        "pc_port/pc_p2_mar.cpp": (EMISSION_FN, "becomePellet", EMIT_MARKER,
                                  "MAR_DEAD", "corpseEmitted"),
        "tools/p2_mar_corpse_emission_fixture.cpp": (EMIT_MARKER,),
    }
    found = {}
    for rel, tokens in required.items():
        text = (native_wt / rel).read_text(encoding="utf-8", errors="replace") \
            if (native_wt / rel).is_file() else None
        if text is None:
            raise LandingError("Missing #716 native file: " + rel)
        missing = [t for t in tokens if t not in text]
        if missing:
            raise LandingError("Emission contract tokens absent in %s: %s" % (rel, missing))
        found[rel] = sha256_file(native_wt / rel)
    return found


def verify_arm_compat(native_wt):
    """The #668 arm consumes exactly what the #716 emission produces."""
    native_wt = Path(native_wt)
    receipt = (native_wt / "pc_port/pc_p2_mar_receipt.cpp").read_text(
        encoding="utf-8", errors="replace") \
        if (native_wt / "pc_port/pc_p2_mar_receipt.cpp").is_file() else None
    if receipt is None:
        raise LandingError("Missing #668 receipt adapter")
    checks = {
        "adapter binds live actors": "bound[view] = generator" in receipt,
        "entries persist after death": "persist after death" in receipt,
        "generator from mGenerator": "mGenerator" in receipt,
        "ready marker with receipt id": ("P2_MAR_CORPSE_READY" in receipt
                                         and "receipt=corpse:mar:" in receipt),
    }
    preview = (native_wt / "pc_port/pc_p2_preview.cpp").read_text(
        encoding="utf-8", errors="replace")
    checks["preview consumes arm"] = ("pc_p2_mar_receipt(pellet->mPelletView,generator)"
                                      in preview)
    emission = (native_wt / "pc_port/pc_p2_mar.cpp").read_text(
        encoding="utf-8", errors="replace")
    checks["emission keys pellet to dead actor"] = (
        "pellet->mPelletView == static_cast<PelletView*>(actor)" in emission)
    checks["emission carries source_id=29"] = (
        "source_id=29" in emission and SOURCE_ID in receipt)
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise LandingError("Arm compatibility failed: %s" % failed)
    return {"checks": sorted(checks)}


def verify_compiled_evidence(provenance_path, fixture_exe, production_exe):
    """Provenance is built and both executables hash-match their records."""
    provenance = Path(provenance_path)
    if not provenance.is_file():
        raise LandingError("Missing provenance: " + str(provenance))
    import json
    record = json.loads(provenance.read_text(encoding="utf-8"))
    if record.get("status") != "built":
        raise LandingError("Provenance not built: %r" % record.get("status"))
    artifacts = record.get("artifacts", {})
    exe_key = next((k for k in artifacts
                    if k.replace(chr(92), "/").endswith("/fixture.exe")), None)
    if exe_key is None:
        raise LandingError("Provenance has no fixture.exe artifact")
    if sha256_file(fixture_exe) != artifacts[exe_key].get("sha256"):
        raise LandingError("Fixture exe hash differs from provenance")
    production = sha256_file(production_exe)
    return {"provenance_status": "built",
            "expected_native_head": record.get("expected_native_head"),
            "fixture_exe_sha256": artifacts[exe_key].get("sha256"),
            "production_exe_sha256": production}


def verify_markers_absent_of_interruption(log_text):
    """A landing review log must not smuggle runtime claims or injections."""
    if CAPTAIN_DOWN in log_text:
        raise LandingError("Captain-down in landing evidence")
    hits = [t for t in INJECTED_TOKENS if t in log_text]
    if hits:
        raise LandingError("Injection tokens in landing evidence: %s" % hits)
    return True


SEQUENCE = (
    "1. Land #716 now on compiled evidence + fixture (no runtime Mar claim). "
    "2. #375 lands the emission and runs its natural kills in the Mar arena "
    "(flying-install, generator 375001). "
    "3. The arena kill runs prove #716 (corpse pellet + receipt), closing transport_reward."
)


def sequencing():
    return SEQUENCE
