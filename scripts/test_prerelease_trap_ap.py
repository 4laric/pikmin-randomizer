"""Packaged AP Prerelease trap classification, YAML option and restrictive fills."""
import importlib,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_apworld import build
sys.path.insert(0,sys.argv[1])
import ModuleUpdate
ModuleUpdate.update_ran=True
import worlds
from test.general import setup_multiworld
from BaseClasses import CollectionState,ItemClassification
from Fill import distribute_items_restrictive
with tempfile.TemporaryDirectory() as folder:
    archive=build(Path(folder)/'pikmin_randomizer.apworld');sys.path.insert(0,str(archive))
    mod=importlib.import_module('pikmin_randomizer')
    for seed in range(30):
        options=dict(prerelease_trap_weight=(1,5,10)[seed%3],bomb_trap_weight=seed%2,bomb_rock_weight=seed%2,campaign_enemies=True,permanent_checks=True,progressive_color_stats=True,starting_area=(0,1,3,4,5)[seed%5],starting_color=seed%3)
        mw=setup_multiworld(mod.PikminRandomizerWorld,seed=seed,options=options)
        traps=[item for item in mw.itempool if item.name=='Faithful to Prerelease']
        assert traps and all(item.classification==ItemClassification.trap for item in traps)
        assert mw.worlds[1].manifest()['prerelease_trap_weight']==options['prerelease_trap_weight']
        distribute_items_restrictive(mw)
        state=CollectionState(mw);remaining=list(mw.get_locations())
        while remaining:
            reachable=[loc for loc in remaining if loc.can_reach(state)]
            assert reachable,[loc.name for loc in remaining]
            for loc in reachable:
                state.collect(loc.item,True);remaining.remove(loc)
        assert mw.can_beat_game()
    mw=setup_multiworld(mod.PikminRandomizerWorld,seed=100)
    assert not any(item.name=='Faithful to Prerelease' for item in mw.itempool)
print('PASS 30 packaged AP Prerelease trap fills across five areas; trap classification and default-disabled pool')
