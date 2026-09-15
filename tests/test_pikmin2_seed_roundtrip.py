"""Lane 03 (#439): the post-load resolve validator flips without P2_SEED_RESOLVE.

Pure-Python. Verifies that the root-side gate-1 validator passes on a
representative captured log, and that stripping the ``P2_SEED_RESOLVE`` marker
from an otherwise identical log flips the result to a failure (the marker — not
any incidental line — is what carries the Snow / Dwarf Orange binding).

A second, unskipped-when-present source-text check pins the native emission and
cache sites through ``PIKMIN_NATIVE_ROOT`` (a native repo root, probed via its
``pc_port/`` subdir and ``src/`` tree) so the marker is backed by the real
``GenObjectTeki::birth`` hook and the ramMode SLT1-cache condition. No lane paths
appear anywhere in this file; without ``PIKMIN_NATIVE_ROOT`` the source-check
class skips cleanly.
"""
import os
import unittest
from pathlib import Path

from experimental.pikmin2_seed_roundtrip import (
    ORANGE_SOURCE,
    SNOW_SOURCE,
    parse_resolves,
    validate_log,
)

ROOT = Path(__file__).resolve().parents[1]

SAMPLE_LOG = """\
P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3 x=1143751.0 z=7210.0
P2_SEED_RESOLVE source_id=45 target=328297937 original_type=3 x=-8999.0 z=12340.0
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=3276 x=1.0 y=2.0 z=3.0 health=300.0 max_health=300.0 behavior=P1
"""

DWARF_ORANGE_LOG = """\
P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3 x=1143751.0 z=7210.0
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=3276 x=1.0 y=2.0 z=3.0 health=300.0 max_health=300.0 behavior=P1
"""


def _strip_marker(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if "P2_SEED_RESOLVE" not in line)


def test_validator_passes_on_real_resolve_log():
    result = validate_log(SAMPLE_LOG)
    assert result.ok, result.reason
    assert result.sources == {SNOW_SOURCE, ORANGE_SOURCE}
    assert len(result.targets) == 2


def test_validator_flips_when_resolve_marker_is_stripped():
    result = validate_log(_strip_marker(SAMPLE_LOG))
    assert not result.ok
    assert "no P2_SEED_RESOLVE" in result.reason


def test_validator_flips_on_non_cohort_source():
    bogus = SAMPLE_LOG.replace("source_id=45", "source_id=15")
    result = validate_log(bogus)
    assert not result.ok
    assert "non-cohort" in result.reason


def test_validator_requires_family_ready_when_asked():
    # Every resolved source must have a family READY line when required.
    assert validate_log(DWARF_ORANGE_LOG, require_ready=True).ok
    result = validate_log(SAMPLE_LOG, require_ready=True)  # resolves Snow(45) with no READY yet
    assert not result.ok
    assert "READY" in result.reason


def _native_root() -> Path | None:
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if root and (Path(root) / "pc_port" / "pc_randomizer.cpp").is_file():
        return Path(root).resolve()
    candidate = ROOT / "native"
    if (candidate / "pc_port" / "pc_randomizer.cpp").is_file():
        return candidate.resolve()
    return None


def _read(rel: str) -> str:
    native = _native_root()
    if native is None:
        return ""
    path = native / rel
    return path.read_text(errors="replace") if path.is_file() else ""


@unittest.skipUnless(_native_root(), "native worktree not available (set PIKMIN_NATIVE_ROOT)")
class NativeSourcePinTests(unittest.TestCase):
    def test_birth_hook_emits_resolve_marker(self):
        self.assertIn("P2_SEED_RESOLVE", _read("src/plugPikiNakata/genteki.cpp"))

    def test_generator_slt1_cache_covers_p2_bridge(self):
        self.assertIn("pc_randomizer_p2_bridge()", _read("src/plugPikiKando/generator.cpp"))
