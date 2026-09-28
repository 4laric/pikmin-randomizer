"""Landing validator for the #698 impact squad-spawn diagnosis (issue #733).

Re-verifies the done-but-unlanded #698 diagnosis read-only (no source,
shared, native or family edits; no builds; no runtime; no ADMIT) and
validates the fixture-gating verdict plus the #649 fix location, so the
single-writer integrator can land it for downstream consumer #565. All inputs
are explicit paths; every check is fail-closed and every finding carries
hashes.
"""
import hashlib
import re
import subprocess
from pathlib import Path

VERDICTS = ("stall-post-park", "progressed", "captain-interrupted",
            "empty-log", "no-park-marker", "unknown")
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
    with open(path, "rb") as stream:
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
    """The exact #698 commit exists with the expected subject."""
    actual = git(repo, "rev-parse", sha)
    if actual != sha:
        raise LandingError("Commit not found: " + sha)
    subject = git(repo, "log", "--format=%s", "-1", sha)
    if subject_fragment not in subject:
        raise LandingError("Commit subject drift: %r" % subject)
    return {"sha": sha, "subject": subject}


def verify_diagnosis_files(root_wt):
    """The three #698 files exist with the classifier contract tokens."""
    root_wt = Path(root_wt)
    required = {
        "experimental/pikmin2_impact_squad_spawn_diagnosis.py": (
            "stall-post-park", "P2_CHALLENGE_PARK", "P2_CHALLENGE_SQUAD"),
        "tests/test_pikmin2_impact_squad_spawn_diagnosis.py": (
            "stall-post-park",),
        "docs/PIKMIN2_IMPACT_SQUAD_SPAWN_DIAGNOSIS.md": (
            "fixture-observation freeze", "per-gate instrumentation"),
    }
    found = {}
    for rel, tokens in required.items():
        candidate = root_wt / rel
        if not candidate.is_file():
            raise LandingError("Missing #698 file: " + rel)
        text = candidate.read_text(encoding="utf-8", errors="replace")
        missing = [t for t in tokens if t not in text]
        if missing:
            raise LandingError("Diagnosis contract tokens absent in %s: %s" % (rel, missing))
        found[rel] = sha256_file(candidate)
    return found


def verify_fix_location(native649_wt):
    """The #649 fixture idle() carries the exact gates the fix must instrument."""
    candidate = Path(native649_wt) / "tools/p2_challenge_guarded_boot_fixture.cpp"
    if not candidate.is_file():
        raise LandingError("Missing #649 fixture: " + str(candidate))
    text = candidate.read_text(encoding="utf-8", errors="replace")
    required = (
        "alivePikis", "frames<20000", "getNavi()", "mMoviePlayer",
        "mPauseAll", "mIsUIOverlayActive", "P2_CHALLENGE_PARK",
        "P2_CHALLENGE_SQUAD", "P2_CHALLENGE_BOOT",
        "PASS P2_CHALLENGE_GUARDED_BOOT",
        "p2_fixture_require_captain",
    )
    missing = [t for t in required if t not in text]
    if missing:
        raise LandingError("Fix-location gates absent in #649 fixture: %s" % missing)
    lines = text.splitlines()
    gates = {}
    for token in ("alivePikis()", "P2_CHALLENGE_PARK", "P2_CHALLENGE_SQUAD",
                  "P2_CHALLENGE_BOOT", "PASS P2_CHALLENGE_GUARDED_BOOT"):
        gates[token] = next((n + 1 for n, line in enumerate(lines) if token in line), None)
    if any(v is None for v in gates.values()):
        raise LandingError("Fix-location gate lines unmappable")
    return {"sha256": sha256_file(candidate), "gate_lines": gates}


def verify_consumer_runs(runs_dir):
    """The 7 shaped 799-line PARK logs plus 1 empty log, exactly as diagnosed."""
    runs_dir = Path(runs_dir)
    if not runs_dir.is_dir():
        raise LandingError("Missing consumer runs dir: " + str(runs_dir))
    shaped, empty, other = [], [], []
    for child in sorted(runs_dir.iterdir()):
        log = child / "native.log"
        if not log.is_file():
            continue
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            empty.append(child.name)
        elif len(lines) == 799 and any("P2_CHALLENGE_PARK" in line for line in lines):
            shaped.append(child.name)
        else:
            other.append((child.name, len(lines)))
    if len(shaped) != 7 or len(empty) != 1 or other:
        raise LandingError("Consumer run shape drift: shaped=%d empty=%d other=%s"
                           % (len(shaped), len(empty), other))
    return {"shaped": shaped, "empty": empty}


def verify_markers_absent_of_interruption(log_text):
    """A landing review log must not smuggle runtime claims or injections."""
    if CAPTAIN_DOWN in log_text:
        raise LandingError("Captain-down in landing evidence")
    hits = [t for t in INJECTED_TOKENS if t in log_text]
    if hits:
        raise LandingError("Injection tokens in landing evidence: %s" % hits)
    return True


SEQUENCE = (
    "1. Land #698 now on diagnosis evidence (no runtime claim). "
    "2. #649 owner adds the per-gate diagnostic markers plus alivePikis counts "
    "to the fixture idle() at the located gates. "
    "3. #565 reruns its guarded chal0 boot; the markers separate "
    "squad-never-spawned from observation-frozen, and squad spawn is observed."
)


def sequencing():
    return SEQUENCE
