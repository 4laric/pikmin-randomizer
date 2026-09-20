"""Product seed API/CLI wiring for the versioned P2 density policy (#841).

#838 added the versioned policy to the placement bridge
(``experimental/pikmin2_seed_bridge.py``). This slice wires it through the
product entry points without changing legacy behaviour:

* ``randomizer.seed.generate(..., p2_density=...)`` forwards the policy into
  ``resolve_placement_layout`` and stores it on ``p2_layout``.
* the ``python -m randomizer generate`` CLI exposes ``--p2-density``.

The legacy default (``None``) stays the unchanged all-target fill; a bounded
request binds only the minimum accepted targets that cover each selected
species; an unknown token fails closed. These tests use the committed
accepted-placement document and the real roster, exactly like
``tests/test_p2_species_density.py``.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from experimental.pikmin2_seed_bridge import DENSITY_BOUNDED, DENSITY_LEGACY
from randomizer.seed import fingerprint, generate, validate

ROOT = Path(__file__).resolve().parents[1]
SARAI = 23
OTAKARA = [59, 60, 61, 62]

# Fingerprints captured on the pre-wiring tree (48a2a693). Adding the explicit
# parameter must not perturb any existing seed, P2 or not.
LEGACY_FINGERPRINT = "7b99245bc9f541e0ff13d35429c0f244ae787c1716c013d6f2020235a6c71a79"
P2_LEGACY_FINGERPRINT = "c32c0f02bf8b8001299144fee85f755705ca49d7f13c41d4e5a6cd7d5137163f"


def p2_manifest(seed="seed-a", species=None, density=None):
    return generate(seed, p2_enemies=True, p2_species=species, p2_density=density)


def sources(manifest):
    return sorted(binding["source_id"] for binding in manifest["p2_layout"]["bindings"])


def run_cli(*arguments):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "randomizer", *arguments],
                          cwd=str(ROOT), env=env, capture_output=True, text=True)


# --- product API: legacy default unchanged ----------------------------------


def test_legacy_default_is_the_all_target_fill():
    manifest = p2_manifest(species=[SARAI])
    assert manifest["p2_layout"]["density"] == DENSITY_LEGACY
    assert len(manifest["p2_layout"]["bindings"]) == 33
    assert set(sources(manifest)) == {SARAI}


def test_explicit_legacy_equals_the_default():
    assert p2_manifest(species=[SARAI]) == p2_manifest(species=[SARAI], density=DENSITY_LEGACY)


def test_legacy_fingerprints_are_stable():
    assert fingerprint(generate("12345")) == LEGACY_FINGERPRINT
    assert fingerprint(p2_manifest(species=[SARAI])) == P2_LEGACY_FINGERPRINT


# --- product API: bounded coverage ------------------------------------------


def test_bounded_one_species_binds_the_minimum():
    manifest = p2_manifest(species=[SARAI], density=DENSITY_BOUNDED)
    assert manifest["p2_layout"]["density"] == DENSITY_BOUNDED
    assert len(manifest["p2_layout"]["bindings"]) == 1
    assert sources(manifest) == [SARAI]


def test_bounded_multispecies_covers_each_species_once():
    manifest = p2_manifest(species=OTAKARA, density=DENSITY_BOUNDED)
    assert len(manifest["p2_layout"]["bindings"]) == len(OTAKARA)
    assert sources(manifest) == sorted(OTAKARA)


def test_bounded_is_deterministic():
    kwargs = dict(species=[SARAI, 44], density=DENSITY_BOUNDED)
    assert p2_manifest(**kwargs) == p2_manifest(**kwargs)


# --- product API: fail-closed handling --------------------------------------


def test_density_requires_p2_enemies():
    with pytest.raises(ValueError):
        generate("seed-a", p2_density=DENSITY_BOUNDED)


def test_unknown_density_fails_closed():
    with pytest.raises(ValueError):
        p2_manifest(species=[SARAI], density="not-a-policy")


# --- manifest round trips ---------------------------------------------------


def test_manifest_round_trip_preserves_density():
    manifest = p2_manifest(species=[SARAI, 44], density=DENSITY_BOUNDED)
    loaded = json.loads(json.dumps(manifest))
    validate(loaded)
    assert loaded["p2_layout"] == manifest["p2_layout"]
    assert loaded["p2_layout"]["density"] == DENSITY_BOUNDED


def test_legacy_manifest_without_density_still_validates():
    manifest = p2_manifest(species=[SARAI])
    stripped = json.loads(json.dumps(manifest))
    stripped["p2_layout"].pop("density")
    validate(stripped)  # absent policy means legacy; never rejected


def test_tampered_density_is_rejected():
    manifest = p2_manifest(species=[SARAI], density=DENSITY_BOUNDED)
    manifest["p2_layout"]["density"] = "untrusted-token"
    with pytest.raises(ValueError):
        validate(manifest)


# --- product CLI ------------------------------------------------------------


def test_cli_bounded_seed(tmp_path):
    output = tmp_path / "bounded.json"
    result = run_cli("generate", "--seed", "cli-bounded", "--p2-enemies",
                     "--p2-species", str(SARAI), "--p2-density", DENSITY_BOUNDED,
                     "--output", str(output))
    assert result.returncode == 0, result.stderr
    manifest = json.loads(output.read_text(encoding="utf-8"))
    validate(manifest)
    assert manifest["p2_layout"]["density"] == DENSITY_BOUNDED
    assert len(manifest["p2_layout"]["bindings"]) == 1


def test_cli_default_is_legacy(tmp_path):
    output = tmp_path / "legacy.json"
    result = run_cli("generate", "--seed", "cli-legacy", "--p2-enemies",
                     "--p2-species", str(SARAI), "--output", str(output))
    assert result.returncode == 0, result.stderr
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["p2_layout"]["density"] == DENSITY_LEGACY
    assert len(manifest["p2_layout"]["bindings"]) == 33


def test_cli_rejects_unknown_density(tmp_path):
    output = tmp_path / "bad.json"
    result = run_cli("generate", "--seed", "cli-bad", "--p2-enemies",
                     "--p2-density", "not-a-policy", "--output", str(output))
    assert result.returncode != 0
    assert not output.exists()
