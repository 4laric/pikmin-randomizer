"""Universal Tracker regeneration: default options plus re_gen_passthrough must reproduce the original slot."""
import argparse
import importlib
import sys
import tempfile
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_apworld import build


def main(ap):
    sys.path.insert(0, str(ap))
    import ModuleUpdate
    ModuleUpdate.update_ran = True
    import worlds
    from test.general import setup_multiworld
    from Fill import distribute_items_restrictive
    from BaseClasses import CollectionState, MultiWorld
    from randomizer.catalog import GAME, ITEM_IDS
    with tempfile.TemporaryDirectory() as temp:
        archive = build(Path(temp) / "pikmin_randomizer.apworld")
        sys.path.insert(0, str(archive))
        mod = importlib.import_module("pikmin_randomizer")
        assert mod.PikminRandomizerWorld.ut_can_gen_without_yaml
        variants = [
            dict(starting_area=2, starting_color=3, randomize_color_stats=True, progressive_color_stats=True, campaign_enemies=True, death_link=True, death_link_pikmin=25),
            dict(starting_area=4, starting_color=2, starting_flarlic=3, group_spawn_enemies=True, bomb_trap_weight=2, progg_trap_weight=1),
            dict(goal=0, collection_checks=False, enemy_shuffle=True, starting_area=1),
        ]
        checked = 0
        for seed, options in enumerate(variants * 4):
            original = setup_multiworld(mod.PikminRandomizerWorld, seed=seed, options=options)
            original.seed_name = f"room-{seed}"
            slot_data = mod.PikminRandomizerWorld.interpret_slot_data(original.worlds[1].fill_slot_data())
            assert slot_data is not None
            # UT builds a fresh multiworld with default options and a different seed name.
            init = MultiWorld.__init__
            def patched(self, *args, **kwargs):
                init(self, *args, **kwargs)
                self.re_gen_passthrough = {GAME: slot_data}
                self.generation_is_fake = True
            MultiWorld.__init__ = patched
            try:
                regen = setup_multiworld(mod.PikminRandomizerWorld, seed=9000 + seed, options={})
            finally:
                MultiWorld.__init__ = init
            regen.seed_name = "universal-tracker"
            assert regen.worlds[1].manifest() == original.worlds[1].manifest()
            assert {l.name: l.address for l in regen.get_locations()} == {l.name: l.address for l in original.get_locations()}
            assert Counter(i.name for i in regen.itempool) == Counter(i.name for i in original.itempool)
            regen.worlds[1].generate_output(temp)  # No-op during fake generation.
            assert not list(Path(temp).glob("*.pikmin.json"))
            # Same received items give the same in-logic set in both worlds.
            for count in (0, 3, 8, len(original.itempool)):
                states = []
                for mw in (original, regen):
                    state = CollectionState(mw)
                    for item in sorted(mw.itempool, key=lambda i: i.name)[:count]:
                        state.collect(mw.worlds[1].create_item(item.name), True)
                    states.append({l.name for l in mw.get_locations() if l.can_reach(state)})
                assert states[0] == states[1], (seed, count)
                checked += 1
            distribute_items_restrictive(regen)
            assert regen.can_beat_game() and not regen.get_unfilled_locations()
        print(f"Universal Tracker regeneration: {len(variants) * 4} slots reproduced; {checked} reachability snapshots match; regen fills pass")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ap", type=Path); main(p.parse_args().ap)
