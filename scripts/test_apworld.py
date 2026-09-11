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
              mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed, options={"collection_checks": False, "expanded_checks": expanded, "starting_area": start, "starting_color": color, 'all_areas': all_areas})
              mw.seed_name = str(seed)
              world = mw.worlds[1]
              assert len(mw.get_locations()) == (58 if world.manifest()['schema'] >= 5 else 55 if world.manifest()['schema'] >= 2 else 30)
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
        for seed in range(100):
            mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed,
                                 options={'collection_checks': False, 'enemy_shuffle': True, 'starting_area': 2, 'starting_color': 3})
            assert mw.worlds[1].manifest()['schema'] == 6
            distribute_items_restrictive(mw)
            assert mw.can_beat_game() and not mw.get_unfilled_locations()
        for initial in (1, 2, 10):
            for seed in range(20):
                mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed,
                                     options={'starting_flarlic': initial, 'collection_checks': bool(seed % 2)})
                m = mw.worlds[1].manifest()
                assert m['starting_flarlic'] == initial
                assert sum(item.name == FLARLIC for item in mw.itempool) == 10 - initial
                distribute_items_restrictive(mw)
                assert mw.can_beat_game() and not mw.get_unfilled_locations()
        for seed in range(100):
            mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed,
                                 options={'randomize_color_stats': True, 'starting_area': 2,
                                          'starting_color': 3, 'collection_checks': bool(seed % 2)})
            assert 'color_stats' in mw.worlds[1].manifest()
            distribute_items_restrictive(mw)
            assert mw.can_beat_game() and not mw.get_unfilled_locations()
        for seed in range(100):
            mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed,
                                 options={'progressive_color_stats': True, 'randomize_color_stats': bool(seed % 2), 'starting_area': 2, 'starting_color': 3})
            distribute_items_restrictive(mw)
            assert mw.can_beat_game() and not mw.get_unfilled_locations()
        for seed in range(100):
            mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed,
                                 options={'permanent_checks': True, 'progressive_color_stats': True,
                                          'randomize_color_stats': True, 'starting_area': 2, 'starting_color': 3})
            assert len(mw.get_locations()) > 64
            distribute_items_restrictive(mw)
            assert mw.can_beat_game() and not mw.get_unfilled_locations()
        # Explicitly fill every enemy permutation across all starts/colors.
        from randomizer.enemies import resolve_layout
        for mask in range(8):
            for area in (0, 1, 3, 4, 5):
                for color in range(3):
                    mw = setup_multiworld(mod.PikminRandomizerWorld, seed=1000 + mask*100 + area*10 + color,
                        options={'enemy_shuffle': True, 'permanent_checks': True, 'progressive_color_stats': True,
                                 'randomize_color_stats': True, 'starting_area': area, 'starting_color': color})
                    m = mw.worlds[1].manifest()
                    m['enemy_mask'] = mask; m['enemy_shuffle'] = 'families-v1' if mask else 'none'
                    m['enemy_layout'] = resolve_layout(mask); validate(m)
                    distribute_items_restrictive(mw)
                    assert mw.can_beat_game() and not mw.get_unfilled_locations(), (mask,area,color)
        # A two-slot fill exercises cross-player rewards instead of only solo AP.
        for seed in range(100):
            mw = setup_multiworld(mod.PikminRandomizerWorld, seed=seed,
                                 options={'collection_checks': True, 'enemy_shuffle': bool(seed % 2), 'starting_area': 2, 'starting_color': 3})
            assert mw.worlds[1].manifest()['schema'] == 9
            distribute_items_restrictive(mw)
            assert mw.can_beat_game() and not mw.get_unfilled_locations()
        mw = setup_multiworld([mod.PikminRandomizerWorld] * 2, seed=211, options=[{"collection_checks": False, "expanded_checks": True, "starting_area": 4, "starting_color": 0, 'enemy_shuffle': True}, {"collection_checks": False, "expanded_checks": True}])
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
        initial.collect(mw.worlds[1].create_item(FLARLIC), True)
        initial.collect(blue, True)
        assert water.can_reach(initial)
        distribute_items_restrictive(mw)
        assert mw.can_beat_game()
        assert any(loc.item.player != loc.player for loc in mw.get_locations())
        assert remote.item.player == 1 and remote.player == 2
        mw = setup_multiworld([mod.PikminRandomizerWorld] * 2, seed=291,
                             options=[{'progressive_color_stats': True}, {'progressive_color_stats': True}])
        carry = next(item for item in mw.itempool if item.player == 1 and item.name == 'Progressive Red Carry Strength')
        mw.itempool.remove(carry)
        remote = mw.get_location('Population: 20 total Pikmin', 2)
        remote.place_locked_item(carry)
        initial = CollectionState(mw)
        initial.collect(mw.worlds[1].create_item(FLARLIC), True)
        part = mw.get_location('Pikmin: Eternal Fuel Dynamo', 1)
        assert not part.can_reach(initial) and remote.can_reach(initial)
        initial.collect(carry, True)
        assert part.can_reach(initial)
        distribute_items_restrictive(mw)
        assert mw.can_beat_game() and not mw.get_unfilled_locations()
        # Remote area access gates the species moved there by the seed's swap.
        mw = setup_multiworld([mod.PikminRandomizerWorld] * 2, seed=369,
            options=[{'enemy_shuffle': True, 'collection_checks': True}, {'collection_checks': True}])
        m=mw.worlds[1].manifest(); m['enemy_mask']=2; m['enemy_shuffle']='families-v1'; m['enemy_layout']=resolve_layout(2)
        access=next(item for item in mw.itempool if item.player==1 and item.name=='Pikmin: Distant Spring Access')
        mw.itempool.remove(access)
        remote=mw.get_location('Population: 20 total Pikmin',2); remote.place_locked_item(access)
        initial=CollectionState(mw)
        for name in ('Yellow Onion','Blue Onion'): initial.collect(mw.worlds[1].create_item(name),True)
        moved=mw.get_location('Bestiary: Deliver Spotty Bulborb',1)
        assert not moved.can_reach(initial) and remote.can_reach(initial)
        initial.collect(access,True); assert moved.can_reach(initial)
        distribute_items_restrictive(mw); assert mw.can_beat_game() and not mw.get_unfilled_locations()
        print(f"Packaged AP world: {len(configs)*100+200} single-slot fills plus 60 starting-Flarlic, 100 color-stat, 100 progressive-stat and 100 permanent-check fills, plus 120 explicit enemy-layout fills; remote-Blue, remote-Carry and remote-enemy-area two-slot fills pass")

if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("ap", type=Path);main(p.parse_args().ap)
