"""Package-local per-spawn AP fills and every-check reachability."""
import importlib, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_apworld import build
sys.path.insert(0,sys.argv[1])
import ModuleUpdate
ModuleUpdate.update_ran=True
import worlds
campaign='--campaign' in sys.argv[2:]
groups='--groups' in sys.argv[2:]
miniboss='--miniboss' in sys.argv[2:]
from test.general import setup_multiworld
from BaseClasses import CollectionState
from Fill import distribute_items_restrictive

def complete(mw):
    distribute_items_restrictive(mw)
    state=CollectionState(mw);remaining=list(mw.get_locations())
    while remaining:
        reachable=[loc for loc in remaining if loc.can_reach(state)]
        assert reachable, [loc.name for loc in remaining]
        for loc in reachable:
            assert loc.item is not None
            state.collect(loc.item,True)
            remaining.remove(loc)
    assert mw.can_beat_game()

with tempfile.TemporaryDirectory() as folder:
    archive=build(Path(folder)/'pikmin_randomizer.apworld');sys.path.insert(0,str(archive))
    mod=importlib.import_module('pikmin_randomizer')
    if '--balance' in sys.argv:
        import yaml
        example = yaml.safe_load((ROOT / 'examples/Player1.yaml').read_text(encoding='utf-8'))
        options = example['Pikmin Randomizer']
        mw = setup_multiworld(mod.PikminRandomizerWorld, seed=7023, options=options)
        complete(mw)
        assert mw.worlds[1].manifest()['stat_upgrade_counts'] == dict(damage=4, movement=2, attack_rate=2, carry=4)
    for seed in range(0 if '--yaml-only' in sys.argv else 150):
        options=dict(campaign_enemies=campaign,per_spawn_enemies=True,group_spawn_enemies=groups,miniboss_enemies=miniboss,enemy_shuffle=True,starting_area=(0,1,3,4,5)[seed%5],starting_color=(seed//5)%3,
                     starting_flarlic=1,permanent_checks=bool(seed%2),randomize_color_stats=True,progressive_color_stats=True)
        if '--balance' in sys.argv:
            options.update(initial_damage_min=50, initial_damage_max=50, initial_movement_min=25, initial_movement_max=50,
                           damage_upgrades=seed % 5, movement_upgrades=seed % 3, attack_rate_upgrades=(seed // 3) % 3, carry_upgrades=(seed // 5) % 5,
                           starting_area=2, random_start_areas={'spring', 'impact'})
        mw=setup_multiworld(mod.PikminRandomizerWorld,seed=seed,options=options)
        if '--balance' in sys.argv:
            m = mw.worlds[1].manifest()
            assert m['profile'] in ('spring-day2', 'impact-day2')
            assert all(p['damage'] == 50 and p['movement'] in (25, 50) for p in m['color_stats'].values())
            assert m['stat_upgrade_counts']['damage'] == seed % 5
        assert mw.worlds[1].manifest()['enemy_mask']==0
        complete(mw)
    for seed in range(0 if '--yaml-only' in sys.argv else 10):
        mw=setup_multiworld([mod.PikminRandomizerWorld]*2,seed=seed+4300,
                           options=[dict(campaign_enemies=campaign,per_spawn_enemies=True,group_spawn_enemies=groups,miniboss_enemies=miniboss,starting_area=4,starting_color=0),dict(campaign_enemies=campaign,per_spawn_enemies=True,group_spawn_enemies=groups,miniboss_enemies=miniboss)])
        blue=next(item for item in mw.itempool if item.player==1 and item.name=='Blue Onion')
        mw.itempool.remove(blue)
        mw.get_location('Population: 10 total Red Pikmin',2).place_locked_item(blue)
        complete(mw)
if '--yaml-only' in sys.argv:
    print('PASS YAML example: every check reachable')
else:
    print('PASS 150 per-spawn AP fills and 10 remote-Blue multiworlds; every check reachable; groups=', groups, 'custom balance=', '--balance' in sys.argv)
