"""Packaged AP/UT regression. Does not install or relink any world."""
import argparse
import importlib
import sys
import tempfile
import subprocess
import secrets
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_apworld import build

NATIVE_PROBE = r'''
#include "pc_randomizer.h"
#include <cstdio>
#include <cstring>
#include <cassert>
int main(int argc, char** argv) {
    assert(pc_randomizer_init(argc, argv));
    assert(pc_randomizer_thelynk());
    assert(!pc_randomizer_expanded());
    assert(!pc_randomizer_collection_checks());
    assert(pc_randomizer_next_day(28) == 29);
    assert(pc_randomizer_next_day(29) == 2);
    const char* areas[] = {"Pikmin: Impact Site Access", "Pikmin: Forest of Hope Access", "Pikmin: Forest Navel Access", "Pikmin: Distant Spring Access", "Pikmin: Final Trial Access"};
    std::printf("PARTS %d GOAL %d AREAS", pc_randomizer_repairs(), int(pc_randomizer_goal()));
    for (auto area : areas) std::printf(" %d", int(pc_randomizer_has(area)));
    std::puts("");
    for (int i=1; i<argc; ++i) if (!std::strcmp(argv[i], "--observe")) {
        assert(!pc_randomizer_thelynk_part(0x75737435, false));
        pc_randomizer_thelynk_collect(0x75737435); // ust5 / Main Engine
        assert(pc_randomizer_thelynk_part(0x75737435, false));
        // A physical collection never grants its named reward.
        assert(!pc_randomizer_thelynk_part(0x75737435, true));
        pc_randomizer_thelynk_squad(1, 4, true);
        assert(!pc_randomizer_checked("Red Pikmin: 5"));
        pc_randomizer_thelynk_squad(1, 100, false);
        pc_randomizer_observe_color_population(1, 500, true);
        pc_randomizer_observe_total_population(500, true);
        pc_randomizer_enemy_defeated(16, 0, true, true);
        pc_randomizer_corpse_delivered(3, 0, true);
        assert(!pc_randomizer_checked("Red Pikmin: 5"));
        pc_randomizer_thelynk_squad(1, 5, true);
        assert(pc_randomizer_checked("Red Pikmin: 5"));
        assert(!pc_randomizer_checked("Red Pikmin: 10"));
        pc_randomizer_thelynk_squad(2, 25, true);
        pc_randomizer_thelynk_squad(0, 10, true);
        int used=0;
        for (int k=0;k<18;++k) while(pc_randomizer_thelynk_bonus(k)) {
            std::printf("BONUS %d %d\n",k,pc_randomizer_thelynk_bonus(k));
            pc_randomizer_thelynk_consume(k); ++used;
        }
        std::printf("USED %d\n", used);
    }
    for(int i=1;i<argc;++i) if(!std::strcmp(argv[i],"--save")) {
        char saved[32768]={};saved[123]=42;pc_randomizer_save_campaign(saved);
    }
    if(pc_randomizer_resumed()) {
        char saved[32768]={};assert(pc_randomizer_load_campaign(saved));assert(saved[123]==42);
        for(int k=0;k<18;++k) assert(!pc_randomizer_thelynk_bonus(k));
        std::puts("RESUME_PASS");
    }
    return 0;
}
'''


def native_tests(exe, output):
    from tests.test_compatibility import thelynk_patch
    from randomizer.thelynk import TheLynkSession
    from randomizer.session import atomic_write
    output.mkdir(parents=True, exist_ok=True)
    def run(session, arguments=(), state=None):
        token = secrets.token_hex(32)
        directory = session.directory / "runs" / token
        directory.mkdir(parents=True)
        atomic_write(directory / "bootstrap.txt", session.bootstrap(token))
        atomic_write(directory / "state.txt", session.state(token, True) if state is None else state(token))
        result = subprocess.run([str(exe), "--randomizer-seed", str(directory / "bootstrap.txt"), *arguments],
                                capture_output=True, text=True, timeout=20)
        (directory / "probe.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        return directory, result
    session = TheLynkSession(thelynk_patch(), output / "observations")
    session.bind("12345", 0, 1)
    session.receive(0, list(range(71800, 71818)))
    directory, result = run(session, ("--observe", "--save"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "USED 18" in result.stdout
    assert "PARTS 0 GOAL 0 AREAS 1 0 0 0 0" in result.stdout
    for k in range(18):
        assert f"BONUS {k} {5 if k % 2 else 1}\n" in result.stdout
    session.poll(directory)
    assert set(session.data["checked"]) == {71404,71504,71624,71709}
    _, result = run(session)
    assert result.returncode == 0 and "RESUME_PASS" in result.stdout
    for n in (0,1,4,5,11,12,28,29,30):
        session = TheLynkSession(thelynk_patch(), output / f"parts-{n}")
        session.bind("12345", 0, 1)
        session.receive(0, list(range(71400,71400+n)))
        _, result = run(session)
        expected = f"PARTS {n} GOAL {int(n == 30)} AREAS 1 {int(n >= 1)} {int(n >= 5)} {int(n >= 12)} {int(n >= 29)}"
        assert result.returncode == 0 and expected in result.stdout, result.stdout + result.stderr
    for label, edit in (("foreign-token", lambda s,t: s.replace(t, "b"*64)),
                        ("unknown-check", lambda s,t: s.replace("CHECKS 0", "CHECKS 1 999")),
                        ("invalid-mask", lambda s,t: s.replace(" 1 0 CHECKS", " 1 1073741824 CHECKS"))):
        session = TheLynkSession(thelynk_patch(), output / label)
        session.bind("12345",0,1)
        _, result = run(session, state=lambda token: edit(session.state(token,True),token))
        assert result.returncode != 0, label
    print("PASS: native checks/reward separation, squad thresholds, all 18 bonuses, saved consumption, 9 area/goal boundaries and malformed state rejection")


def main(ap):
    sys.path.insert(0, str(ap))
    import ModuleUpdate
    ModuleUpdate.update_ran = True
    from test.general import setup_multiworld
    from Fill import distribute_items_restrictive
    from BaseClasses import CollectionState
    from randomizer.seed import fingerprint
    with tempfile.TemporaryDirectory() as directory:
        sys.path.insert(0, str(build(Path(directory) / "pikmin_randomizer.apworld")))
        mod = importlib.import_module("pikmin_randomizer")
        World = mod.PikminRandomizerWorld
        for seed in range(12):
            original = setup_multiworld(World, seed=seed, options=dict(
                starting_area=2, starting_color=3, starting_flarlic=1,
                campaign_enemies=bool(seed % 2), progressive_color_stats=bool(seed % 3),
                randomize_color_stats=True, bomb_rock_weight=seed % 3))
            world = original.worlds[1]
            slot = world.fill_slot_data()
            locations = {location.name: location.address for location in original.get_locations()}
            distribute_items_restrictive(original)
            assert original.can_beat_game()
            regenerated = setup_multiworld(World, seed=9999 + seed, steps=())
            tracker = regenerated.worlds[1]
            regenerated.re_gen_passthrough = {World.game: World.interpret_slot_data(slot)}
            tracker.generate_early()
            # Rebuild the generated regions/items under deliberately different defaults.
            tracker.create_regions()
            tracker.create_items()
            tracker.set_rules()
            assert tracker.manifest() == world.manifest()
            assert fingerprint(tracker.manifest()) == slot["manifest_fingerprint"]
            assert {location.name: location.address for location in regenerated.get_locations()} == locations
            for inventory in ({}, {"Ship Repair": 24, "Progressive Flarlic": 5, "Blue Onion": 1},
                              dict.fromkeys(World.item_name_to_id, 40)):
                a, b = CollectionState(original), CollectionState(regenerated)
                for name, count in inventory.items():
                    for _ in range(count):
                        a.collect(world.create_item(name), True)
                        b.collect(tracker.create_item(name), True)
                assert original.completion_condition[1](a) == regenerated.completion_condition[1](b)
                for name in locations:
                    assert original.get_location(name, 1).can_reach(a) == regenerated.get_location(name, 1).can_reach(b)
        for group in World.item_name_groups.values():
            assert group and group <= World.item_name_to_id.keys()
        for group in World.location_name_groups.values():
            assert group and group <= World.location_name_to_id.keys()
        print("PASS: 12 packaged fills and exact UT manifest/location/rule reconstruction; valid groups")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ap", type=Path)
    parser.add_argument("--native-probe", type=Path)
    parser.add_argument("--native-output", type=Path)
    args = parser.parse_args()
    main(args.ap)
    if args.native_probe:
        if not args.native_output:
            parser.error("--native-output is required with --native-probe")
        native_tests(args.native_probe.resolve(), args.native_output.resolve())
