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
        for expanded, start in ((False, 0), (True, 0), (True, 1), (True, 2)):
          for seed in range(100):
              mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed, options={"expanded_checks": expanded, "starting_area": start})
              mw.seed_name = str(seed)
              world = mw.worlds[1]
              assert len(mw.get_locations()) == (55 if expanded else 30)
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
        mw = setup_multiworld([mod.PikminRandomizerWorld] * 2, seed=211, options=[{"expanded_checks": True, "starting_area": 1}, {"expanded_checks": False}])
        mw.seed_name = "two-slot"
        distribute_items_restrictive(mw)
        assert mw.can_beat_game()
        assert any(loc.item.player != loc.player for loc in mw.get_locations())
        print("Packaged AP world: 400 single-slot fills and one mixed-start two-slot fill pass; goal and manifest parity verified")

if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("ap", type=Path);main(p.parse_args().ap)
