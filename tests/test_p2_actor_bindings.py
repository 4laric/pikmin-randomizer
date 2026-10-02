import copy

import pytest

from randomizer.seed import generate, validate
from randomizer.p2_actor_bindings import resolve_actor_bindings
from experimental.pikmin2_seed_bridge import build_bootstrap, resolve_layout


@pytest.fixture(scope="module")
def campaign():
    return generate("1153", campaign_enemies=True, p2_enemies=True,
                    p2_checks=True, p2_species="playable", starting_flarlic=1)


def test_full42_saved_map_matches_native_bootstrap(campaign):
    actors = resolve_actor_bindings(campaign)
    bindings = campaign["p2_layout"]["bindings"]
    assert len({row["source_id"] for row in bindings}) == 42
    wire = build_bootstrap(campaign["p2_layout"]).splitlines()[0].split()[4:]
    assert {target: int(target) for target in wire[::2]} == actors
    assert resolve_actor_bindings(campaign, actors) == actors
    assert resolve_actor_bindings(copy.deepcopy(campaign)) == actors


@pytest.mark.parametrize("value", [True, "12", 0, -1, 2**32, 12.5])
def test_invalid_explicit_generator_refused(campaign, value):
    actors = resolve_actor_bindings(campaign)
    actors[next(iter(actors))] = value
    with pytest.raises(ValueError, match="uint32"):
        resolve_actor_bindings(campaign, actors)


def test_missing_extra_duplicate_and_redirected_campaign_map_refused(campaign):
    actors = resolve_actor_bindings(campaign)
    first, second = list(actors)[:2]
    for bad in ({k: v for k, v in actors.items() if k != first}, dict(actors, extra=19)):
        with pytest.raises(ValueError, match="exactly"):
            resolve_actor_bindings(campaign, bad)
    with pytest.raises(ValueError, match="unique"):
        resolve_actor_bindings(campaign, dict(actors, **{first: actors[second]}))
    with pytest.raises(ValueError, match="match saved"):
        resolve_actor_bindings(campaign, dict(actors, **{first: 42}))


def test_corrupted_saved_catalog_is_not_binding_evidence(campaign):
    bad = copy.deepcopy(campaign)
    uid = int(bad["p2_layout"]["bindings"][0]["target"])
    next(row for row in bad["enemy_catalog"]["sources"] if row["uid"] == uid)["species"] = 1
    with pytest.raises(ValueError):
        resolve_actor_bindings(bad)


def test_p1_unchanged():
    assert resolve_actor_bindings(generate("plain")) == {}
    with pytest.raises(ValueError, match="P2 layout"):
        resolve_actor_bindings(generate("plain"), {})


def test_campaign_without_optional_checks():
    manifest = generate("normal-content", p2_enemies=True, p2_species="playable")
    assert "enemy_catalog" not in manifest
    assert resolve_actor_bindings(manifest) == {
        row["target"]: int(row["target"]) for row in manifest["p2_layout"]["bindings"]}


@pytest.mark.parametrize("target", ["custom-fixture", "123"])
def test_custom_layout_requires_explicit_map(target):
    manifest = generate("custom-content", p2_enemies=True, p2_species="playable")
    manifest["p2_layout"] = resolve_layout("fixture", "Player1", [target], [44])
    validate(manifest)
    with pytest.raises(ValueError, match="custom P2 layout"):
        resolve_actor_bindings(manifest)
    assert resolve_actor_bindings(manifest, {target: 99}) == {target: 99}
