"""Roster rfix (#871): validate() fail-closed scoping for lost pool admission.

The old ``randomizer/seed.py`` scoping (``admitted | (identity - admitted)``)
was a set-algebra no-op: any installed pool species validated even after
losing roster admission, masked by its installer row. The staging union must
cover only installed-but-unadmitted NON-POOL staging ids
(1,26,27,45,58,66,84,93,97 -- 15 Armor and 25 Wtank graduated to the admitted
pool in admit-frogs5); a pool species that loses admission fails
closed. Each test below fails on the pre-fix scoping.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_seed_bridge as bridge
from randomizer.seed import generate, validate

STAGING_IDS = [1, 45, 66, 97]  # 58 admitted by its OWN port (#244); 26, 27, 84, 93 by #964


@pytest.mark.parametrize("dropped", [34, 70, 2, 44])
def test_lost_pool_admission_fails_closed(dropped, monkeypatch):
    """Dropping an admitted pool id from the admission set must fail validate."""
    manifest = generate("rfix-validate", p2_enemies=True, p2_species="playable")
    bound = {b["source_id"] for b in manifest["p2_layout"]["bindings"]}
    assert dropped in bound
    validate(manifest)  # baseline: the real admission set accepts it

    real_admitted_ids = bridge.admitted_ids

    def without_dropped(roster):
        return [i for i in real_admitted_ids(roster) if i != dropped]

    monkeypatch.setattr(bridge, "admitted_ids", without_dropped)
    with pytest.raises(ValueError, match="invalid p2_layout"):
        validate(manifest)


def test_staging_ids_stay_permitted_for_evidence_runs(monkeypatch):
    """Installed-but-unadmitted staging ids still validate (lane runs in flight)."""
    from experimental.pikmin2_enemy_roster import by_id, load_and_validate

    roster = load_and_validate()
    by_source = by_id(roster)
    manifest = generate("rfix-validate", p2_enemies=True, p2_species="playable")
    # Swap one binding onto a staging identity (Kochappy 1) with its real enum.
    tweaked = dict(manifest)
    bindings = [dict(b) for b in manifest["p2_layout"]["bindings"]]
    bindings[0] = {
        "target": bindings[0]["target"],
        "source_id": 1,
        "enum_name": by_source[1].enum_name,
    }
    layout = dict(manifest["p2_layout"], bindings=bindings)
    tweaked["p2_layout"] = layout
    validate(tweaked)
    assert set(bridge.admitted_ids(roster)) & set(STAGING_IDS) == set()
