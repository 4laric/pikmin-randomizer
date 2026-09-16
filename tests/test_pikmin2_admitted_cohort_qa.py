"""Tests for the admitted nine-identity cohort QA checker (#530).

Engine-free: exercises the real seed/session machinery (generate, layout
validation, bootstrap round-trip, family resolution, manifest save/reload)
on the frozen species pin. Bounded private gameplay startups are staged
separately; see docs/PIKMIN2_ADMITTED_COHORT_QA.md.
"""
import json

import pytest

from experimental import pikmin2_admitted_cohort_qa as cohort_qa


def test_admitted_set_is_exactly_the_approved_nine():
    result = cohort_qa.check_admitted_set()
    assert result["ok"], result["detail"]
    assert result["admitted"] == [23, 44, 54, 57, 59, 60, 61, 62, 78]


@pytest.mark.parametrize("seed", cohort_qa.SEEDS)
def test_representative_seed_manifest_binds_whole_cohort(seed):
    result = cohort_qa.check_seed_manifest(seed)
    assert result["bound"] == cohort_qa.ADMITTED, result
    assert result["foreign_slots"] == [], result
    assert result["layout_ok"], result["layout_detail"]
    assert result["bootstrap_ok"], result["bootstrap_detail"]
    assert result["ok"], result


@pytest.mark.parametrize("seed", cohort_qa.SEEDS)
def test_seed_generation_is_deterministic(seed):
    result = cohort_qa.check_determinism(seed)
    assert result["ok"], result


def test_denied_ids_are_excluded_and_rejected():
    result = cohort_qa.check_denied_exclusion()
    assert result["ok"], json.dumps(result, indent=2)


def test_admitted_install_targets_with_documented_gap():
    # Six admitted IDs resolve to a lane-05 family installer. Newly admitted
    # 54/57/78 have no family installer yet (they stage through the
    # candidate-only muse-packaging sidecar path, which covers 57/78 but not
    # 54); this test pins that exact gap so any change forces a QA update.
    result = cohort_qa.check_install_targets()
    assert result["resolved"] == {23: "sarai", 44: "dwarf_orange",
                                  59: "dweevil", 60: "dweevil",
                                  61: "dweevil", 62: "dweevil"}, result
    assert sorted(result["failures"]) == [54, 57, 78], result
    assert not result["ok"]  # gap open: integrator disposition required


@pytest.mark.parametrize("seed", cohort_qa.SEEDS)
def test_manifest_save_reload_round_trip(seed, tmp_path):
    result = cohort_qa.check_save_restart(seed, tmp_path / seed)
    assert result["same_fingerprint"], result
    assert result["reload_ok"], result["reload_detail"]
    assert result["tamper_rejected"], result
    assert result["ok"], result
