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
    for seed in range(150):
        options=dict(campaign_enemies=campaign,per_spawn_enemies=True,group_spawn_enemies=groups,miniboss_enemies=miniboss,enemy_shuffle=True,starting_area=(0,1,3,4,5)[seed%5],starting_color=(seed//5)%3,
                     starting_flarlic=1,permanent_checks=bool(seed%2),randomize_color_stats=True,progressive_color_stats=True)
        mw=setup_multiworld(mod.PikminRandomizerWorld,seed=seed,options=options)
        assert mw.worlds[1].manifest()['enemy_mask']==0
        complete(mw)
    for seed in range(10):
        mw=setup_multiworld([mod.PikminRandomizerWorld]*2,seed=seed+4300,
                           options=[dict(campaign_enemies=campaign,per_spawn_enemies=True,group_spawn_enemies=groups,miniboss_enemies=miniboss,starting_area=4,starting_color=0),dict(campaign_enemies=campaign,per_spawn_enemies=True,group_spawn_enemies=groups,miniboss_enemies=miniboss)])
        blue=next(item for item in mw.itempool if item.player==1 and item.name=='Blue Onion')
        mw.itempool.remove(blue)
        mw.get_location('Population: 10 total Red Pikmin',2).place_locked_item(blue)
        complete(mw)
print('PASS 150 per-spawn AP fills across all starts/colors and 10 remote-Blue multiworlds; every check reachable; groups=',groups)
