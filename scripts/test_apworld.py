"""Load the packaged world in this process; never install/relink a shared world."""
import argparse
import importlib
import sys
import tempfile
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
    from BaseClasses import CollectionState
    from randomizer.seed import validate, fingerprint
    from randomizer.catalog import REPAIR, UNLOCKS, LOCATION_IDS, FLARLIC
    with tempfile.TemporaryDirectory() as temp:
        archive = build(Path(temp) / "pikmin_randomizer.apworld")
        sys.path.insert(0, str(archive))
        mod = importlib.import_module("pikmin_randomizer")
        configs = [(False, 0, 0, False), (True, 0, 0, False), (True, 1, 0, False), (True, 2, 3, True)]
        configs += [(True, area, color, True) for area in (0, 1, 3, 4, 5) for color in (0, 1, 2)]
        for expanded, start, color, all_areas in configs:
          for seed in range(100):
              mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed, options={"expanded_checks": expanded, "starting_area": start, "starting_color": color, 'all_areas': all_areas})
              mw.seed_name = str(seed)
              world = mw.worlds[1]
              assert len(mw.get_locations()) == (58 if world.manifest()['schema'] >= 5 else 55 if expanded else 30)
              assert len(mw.itempool) == len(mw.get_locations())
              distribute_items_restrictive(mw)
              assert mw.can_beat_game(), seed
              assert not mw.get_unfilled_locations()
              state = CollectionState(mw)
              assert not mw.completion_condition[1](state)
              for _ in range(24): state.collect(world.create_item(REPAIR), True)
              assert not mw.completion_condition[1](state)
              state.collect(world.create_item(REPAIR), True)
              assert mw.completion_condition[1](state)
              data = world.fill_slot_data();validate(data["manifest"])
              assert data["manifest_fingerprint"] == fingerprint(data["manifest"])
        # A two-slot fill exercises cross-player rewards instead of only solo AP.
        mw = setup_multiworld([mod.PikminRandomizerWorld] * 2, seed=211, options=[{"expanded_checks": True, "starting_area": 4, "starting_color": 0}, {"expanded_checks": True}])
        mw.seed_name = "two-slot"
        # Explicitly exercise the requested wait-for-remote-blue scenario.
        blue = next(item for item in mw.itempool if item.player == 1 and item.name == 'Blue Onion')
        mw.itempool.remove(blue)
        remote = mw.get_location('Explore: The Forest of Hope - Land', 2)
        remote.place_locked_item(blue)
        initial = CollectionState(mw)
        water = mw.get_location('Bestiary: Water Dumple', 1)
        assert not water.can_reach(initial)
        assert remote.can_reach(initial)
        initial.collect(blue, True)
        assert water.can_reach(initial)
        distribute_items_restrictive(mw)
        assert mw.can_beat_game()
        assert any(loc.item.player != loc.player for loc in mw.get_locations())
        assert remote.item.player == 1 and remote.player == 2
        print(f"Packaged AP world: {len(configs)*100} single-slot fills and a remote-Blue two-slot fill pass; goal and manifest parity verified")

if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("ap", type=Path);main(p.parse_args().ap)
