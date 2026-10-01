"""Pin a generated journey and an unchanged imported tutorial surface."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.cave_route import Route
from scripts.stage_pikmin2_cave_journey import stage_package as stage_journey
from scripts.stage_pikmin2_surface_water import prepare

ROUTE_START=[-210.,90.,1350.]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_surface(assets,bundle,identity,output,exe,surface,token):
    Route.validate_surface(surface)
    if len(token)!=32 or any(c not in '0123456789abcdef' for c in token):raise ValueError('invalid route token')
    run=prepare(assets,bundle,identity,output)
    directory=run/'assets/dataDir/stages/p2_tutorial'
    if not directory.resolve().is_relative_to(run.resolve()):raise ValueError('private surface generators required')
    # Reuse the validated twenty-Red template, replacing only this private
    # checkpoint roster and spawn. Imported terrain/routes/water stay unchanged.
    for name in ('default.gen','init.gen','plants.gen','day.gen'):
        path=directory/name;blob=bytearray(path.read_bytes())
        struct.pack_into('>3f',blob,4,*surface['position'])
        if name=='default.gen':
            starts=[m.start() for m in re.finditer(b'    0.0v',blob)]+[len(blob)]
            rows=[bytearray(blob[a:b]) for a,b in zip(starts,starts[1:])]
            templates=[row for row in rows if row[72:76]==b'ikip']
            if len(templates)!=20:raise ValueError('current twenty-Red surface template required')
            rows=[row for row in rows if row[72:76]!=b'ikip']
            for i,(species,maturity) in enumerate(surface['squad']):
                baseline=(surface==dict(position=ROUTE_START,health=1.,squad=[[1,0]]*20))
                row=bytearray(templates[i] if baseline else templates[0]);struct.pack_into('<I',row,8,1000+i)
                # First visit retains the existing dry-bank baseline. Reentry
                # places actual survivors on that same audited bank.
                if not baseline:struct.pack_into('>3f',row,48,-190+(i%5)*8,80,1140+(i//5)*8)
                struct.pack_into('>i',row,84,1);struct.pack_into('>i',row,92,species)
                rows.append(row)
            header=blob[:starts[0]];struct.pack_into('>I',header,20,len(rows));blob=header+b''.join(rows)
        path.write_bytes(blob)
    terrain_path=run/'full-surface-inputs.json';terrain=json.loads(terrain_path.read_text())
    terrain['files']={name:sha(run/'assets'/name) for name in terrain['files']}
    terrain.update(starting_pikmin=len(surface['squad']),checkpoint_roster=True,captain_start_xz=[surface['position'][0],surface['position'][2]])
    terrain_path.write_text(json.dumps(terrain,indent=2)+'\n')
    water_path=run/'surface-water-inputs.json';water=json.loads(water_path.read_text())
    water.update(generators_sha256={name:sha(directory/name) for name in ('default.gen','init.gen','plants.gen','day.gen')},
                 starting_squad=surface['squad'],captain_spawn_y=surface['position'][1],
                 captain_start_xz=[surface['position'][0],surface['position'][2]])
    water_path.write_text(json.dumps(water,indent=2)+'\n')
    config='P2_CAVE_ROUTE_SURFACE_1 '+token+' -210 80 1160 60 '+str(surface['health'])+' '+str(len(surface['squad']))+'\n'
    config+=''.join(f'{species} {maturity}\n' for species,maturity in surface['squad'])
    (run/'p2-cave-route-surface.txt').write_text(config)
    shutil.copy2(exe,run/'nectar.exe')
    for dll in exe.parent.glob('*.dll'):shutil.copy2(dll,run/dll.name)
    inputs=['p2-cave-route-surface.txt','nectar.exe','full-surface-inputs.json','surface-water-inputs.json']
    inputs+=['assets/'+name for name in terrain['files']]
    inputs+=['assets/dataDir/courses/p2tutorial/full.water','surface-water.json','assets/dataDir/stages/p2_tutorial/day.gen']
    inputs=sorted(set(inputs))
    (run/'route-surface-inputs.json').write_text(json.dumps(dict(schema=1,receipt_identity=identity,
        starting_party=surface,anchor=[-210,80,1160,60],files={name:sha(run/name) for name in inputs},
        limitations=['Imported terrain and static water; no retail generator actors.',
                     'All living base-color survivors are checkpointed; gathering is not enforced.']),indent=2)+'\n')
    return run,inputs+['route-surface-inputs.json']


def stage_package(seed,slot,assets,pod,exe,generator,bundle,identity,output,workspace):
    stage_journey(seed,slot,assets,pod,exe,generator,output,workspace)
    # Short connected approach: source ground rises50->80 at z1350->1240.
    # Shoreline220,1000 is separated by a ledge and needs a much longer route.
    surface=dict(position=ROUTE_START,health=1.,squad=[[1,0]]*20)
    _,inputs=stage_surface(assets,bundle,identity,output/'surface-blueprint',exe,surface,'0'*32)
    run=output/'surface-blueprint/run'
    record=dict(schema=1,bundle=str(bundle.resolve()),receipt_identity=identity,
                surface=surface,files={name:sha(run/name) for name in inputs},
                geometry={name:sha(run/name) for name in ('assets/dataDir/courses/p2tutorial/full.mod',
                    'assets/dataDir/courses/p2tutorial/full.water')})
    (output/'route-package.json').write_text(json.dumps(record,indent=2)+'\n')
    launcher=Path(__file__).with_name('play_pikmin2_cave_route.py')
    (output/'PlayRoute.cmd').write_text('@echo off\npy -3.12 "'+str(launcher)+'" "'+str(output)+'"\npause\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','pod','exe','generator','bundle','output','workspace'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--identity',required=True);p.add_argument('--seed',default='1154');p.add_argument('--slot',default='Player1')
    a=p.parse_args();print(json.dumps(stage_package(a.seed,a.slot,a.assets,a.pod,a.exe,a.generator,a.bundle,a.identity,a.output,a.workspace),indent=2))
