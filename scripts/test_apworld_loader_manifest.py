"""Regression through a real private AP world loader, YAML generator and fill.

Stage the built .apworld in a PRIVATE AP installation first. This script never
installs or relinks worlds and refuses shared AP/output paths. Dependencies must
already be installed; automatic AP dependency installation is disabled.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def assert_shipped_catalog(manifest, admitted, validate_catalog, locations):
    layout = manifest["p2_layout"]
    selected = {row["source_id"] for row in layout["bindings"]}
    unplaced = set(layout.get("unplaced", []))
    # Boss arena sampling records its unplaced identities separately.
    unplaced.update(layout.get("boss_arenas", {}).get("unplaced", []))
    assert admitted and selected | unplaced == admitted, "shipped YAML narrowed the pinned admitted pool"
    assert layout["density"] == "sampled-v1", "shipped YAML must use sampled density"
    catalog = validate_catalog(manifest["enemy_catalog"], manifest)
    assert {row["game"] for row in catalog["sources"]} == {"p1", "p2"}
    assert {row["species"] for row in catalog["sources"] if row["game"] == "p2"} == selected
    # The packaged validator checks surviving P1 suppliers and all present P2
    # checks, including stable IDs, sources and non-corpse exceptions.
    for row in catalog["checks"]:
        assert locations.get(row["name"]) == row["id"], "resolved check missing from actual AP fill"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ap", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="fresh ignored output directory")
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1153, 1154])
    parser.add_argument("--sample-yaml", type=Path,
                        help="test the shipped player YAML unchanged, twice per seed")
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1]
    common = Path(subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        text=True).strip()).resolve().parent
    ap, output = args.ap.resolve(), args.output.resolve()
    if not ap.is_relative_to(common / "output") or not output.is_relative_to(common / "output"):
        parser.error("AP installation and generated output must both be private under workspace output/")
    if output.exists():
        parser.error("--output must be fresh; existing evidence is never overwritten")
    archive = ap / "custom_worlds/pikmin_randomizer.apworld"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != args.archive_sha256:
        parser.error("private installed APworld hash does not match the selected candidate")
    output.mkdir(parents=True)
    sample_bytes = args.sample_yaml.resolve().read_bytes() if args.sample_yaml else None
    os.chdir(ap)
    # Prevent checkout packages from masking missing archive imports.
    sys.path[:] = [str(ap)] + [p for p in sys.path if p and "pikmin-randomizer" not in p]
    # Exercise AP's supported pure-Python fallback, without compiling optional
    # Cython acceleration into a shared user cache during a loader regression.
    sys.modules["pyximport"] = None
    import ModuleUpdate
    ModuleUpdate.update_ran = True
    import Generate
    import Main
    import yaml
    from BaseClasses import CollectionState
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.pikmin_randomizer.core.seed import fingerprint, validate
    from worlds.pikmin_randomizer.core.enemy_catalog import validate as validate_catalog
    from worlds.pikmin_randomizer.experimental.pikmin2_enemy_roster import load_and_validate, admitted_ids
    world_class = AutoWorldRegister.world_types["Pikmin Randomizer"]
    assert isinstance(world_class.manifest, dict), "actual AP loader must install metadata"
    metadata = dict(world_class.manifest)
    admitted = set(admitted_ids(load_and_validate()))
    assert admitted, "packaged admission cohort is empty"
    cases = [("default", {}), ("disabled", {"p2_enemy_randomizer": False}),
             ("mixed", {"campaign_enemies": True, "p2_enemy_randomizer": True, "p2_enemy_pool": "all"})]
    if sample_bytes is not None:
        cases.extend((("shipped", None), ("shipped-repeat", None)))
    results = []
    for label, options in cases:
        for seed in args.seeds:
            attempt = output / f"{label}-{seed}"
            players = attempt / "players"
            players.mkdir(parents=True)
            if options is None:
                (players / "Player.yaml").write_bytes(sample_bytes)
            else:
                (players / "Player.yaml").write_text(yaml.safe_dump(
                    {"name": "LoaderGate", "game": "Pikmin Randomizer", "Pikmin Randomizer": options}),
                    encoding="utf-8")
            arguments = Generate.mystery_argparse([
                "--seed", str(seed), "--player_files_path", str(players),
                "--outputpath", str(attempt / "generated"), "--spoiler", "2",
                "--weights_file_path", "absent.yaml", "--meta_file_path", "absent-meta.yaml"])
            rolled, actual_seed = Generate.main(arguments)
            world = Main.main(rolled, actual_seed)
            assert not world.get_unfilled_locations()
            assert world.can_beat_game()
            state = CollectionState(world)
            remaining = list(world.get_locations())
            spheres = []
            while remaining:
                reachable = [location for location in remaining if location.can_reach(state)]
                assert reachable, [location.name for location in remaining]
                spheres.append([location.name for location in reachable])
                for location in reachable:
                    state.collect(location.item, True)
                    remaining.remove(location)
            instance = world.worlds[1]
            manifest = instance.seed_manifest()
            validate(manifest)
            assert isinstance(instance.manifest, dict) and instance.manifest == metadata
            assert instance.fill_slot_data()["manifest"] == manifest
            archives = list((attempt / "generated").glob("*.zip"))
            assert len(archives) == 1
            with zipfile.ZipFile(archives[0]) as generated:
                names = [name for name in generated.namelist() if name.endswith(".pikmin.json")]
                assert len(names) == 1
                assert json.loads(generated.read(names[0])) == manifest
            ids = {binding["source_id"] for binding in manifest.get("p2_layout", {}).get("bindings", [])}
            if label in ("mixed", "shipped", "shipped-repeat"):
                assert ids <= admitted and ids
                assert manifest["enemy_composition"] == "p1-then-p2-v1"
                assert "combined-enemies-v1" in manifest["capabilities"]
                assert "p2_proxy_tier" not in manifest
                if label in ("shipped", "shipped-repeat"):
                    assert_shipped_catalog(manifest, admitted, validate_catalog,
                                           {loc.name: loc.address for loc in world.get_locations()})
            else:
                assert "p2_layout" not in manifest
            results.append(dict(label=label, seed=seed, fingerprint=fingerprint(manifest),
                                manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
                                checks=len(world.get_locations()), spheres=spheres, selected_p2_ids=sorted(ids),
                                p2_layout=manifest.get("p2_layout"), enemy_catalog=manifest.get("enemy_catalog")))
            print("ACTUAL LOADER/FILL PASS", label, seed, len(world.get_locations()), flush=True)
    for seed in args.seeds:
        values = {r["label"]: r["fingerprint"] for r in results if r["seed"] == seed}
        assert values["default"] == values["disabled"]
        if sample_bytes is not None:
            assert values["shipped"] == values["shipped-repeat"]
            original = next(r for r in results if r["seed"] == seed and r["label"] == "shipped")
            repeated = next(r for r in results if r["seed"] == seed and r["label"] == "shipped-repeat")
            assert original["manifest_sha256"] == repeated["manifest_sha256"]
            assert original["enemy_catalog"] == repeated["enemy_catalog"]
    (output / "results.json").write_text(json.dumps(dict(
        archive_sha256=args.archive_sha256, metadata=metadata, admitted_ids=sorted(admitted),
        results=results, default_disabled_equal=True,
        shipped_yaml_sha256=hashlib.sha256(sample_bytes).hexdigest() if sample_bytes else None,
        shipped_repeat_equal=sample_bytes is not None,
        scope="Actual AP loader/YAML/fill/slot-output/item-sphere checks; no native gameplay acceptance"),
        indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
