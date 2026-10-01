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
from scripts.stage_pikmin2_playable_cave import (read_species_banks, install_species_banks,
    pin_species_banks, seal_surface_species, stage)

ROUTE_START=[-210.,90.,1350.]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_surface(assets,bundle,identity,output,exe,surface,token,species_banks=None,route_identity=None,*,destination=None):
    Route.validate_surface(surface)
    if len(token)!=32 or any(c not in '0123456789abcdef' for c in token):raise ValueError('invalid route token')
    if destination not in (None,'forest_2/f_02'):raise ValueError('unsupported explicit surface destination')
    # All route banks must be admissible before staging, including unselected
    # banks: the route scope has no Purple impact auxiliary asset bank.
    banks=read_species_banks(species_banks,surface=True)
    requested=sorted({species for species,maturity in surface['squad'] if species>2})
    if requested:
        if any(species not in banks for species in requested): raise ValueError('missing bank for actual surface checkpoint species')
        banks=read_species_banks({species:species_banks[species] for species in requested},surface=True)
        if route_identity is None or route_identity.get('receipt_identity')!=identity:
            raise ValueError('surface species require package-derived route identity')
    else:banks={}
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
                # The generator's legacy color field has only0..2. P/W use
                # baseRed scaffolds; the native versioned checkpoint restores
                # real mutually exclusive species flags and exact maturity.
                struct.pack_into('>i',row,84,1);struct.pack_into('>i',row,92,species if species<=2 else 1)
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
    version=2 if surface.get('wire_schema')==2 else 1
    config=f'P2_CAVE_ROUTE_SURFACE_{version} '+token+' -210 80 1160 60 '+str(surface['health'])+' '+str(len(surface['squad']))+'\n'
    config+=''.join(f'{species} {maturity}\n' for species,maturity in surface['squad'])
    (run/'p2-cave-route-surface.txt').write_text(config)
    destination_files=[]
    if destination is not None:
        (run/'p2-cave-route-destination.txt').write_text(
            f'P2_CAVE_ROUTE_DESTINATION_1 {token} {destination}\n',encoding='ascii')
        destination_files=['p2-cave-route-destination.txt']
    species_files=install_species_banks(run,banks)
    if requested:species_files=seal_surface_species(run,token,route_identity,species_files,requested)
    shutil.copy2(exe,run/'nectar.exe')
    for dll in exe.parent.glob('*.dll'):shutil.copy2(dll,run/dll.name)
    inputs=['p2-cave-route-surface.txt','nectar.exe','full-surface-inputs.json','surface-water-inputs.json']
    inputs+=['assets/'+name for name in terrain['files']]
    inputs+=['assets/dataDir/courses/p2tutorial/full.water','surface-water.json','assets/dataDir/stages/p2_tutorial/day.gen']
    inputs+=species_files
    inputs+=destination_files
    inputs=sorted(set(inputs))
    surface_meta=dict(schema=1,receipt_identity=identity,
        starting_party=surface,anchor=[-210,80,1160,60],files={name:sha(run/name) for name in inputs},
        limitations=['Imported terrain and static water; no retail generator actors.',
                     'Versioned living survivors are checkpointed; gathering is not enforced.'])
    if destination is not None:surface_meta['destination']=destination
    (run/'route-surface-inputs.json').write_text(json.dumps(surface_meta,indent=2)+'\n')
    return run,inputs+['route-surface-inputs.json']


def stage_wfg_journey(seed,slot,assets,pod,exe,generator,output,workspace,species_banks):
    """Separate opt-in package; legacy two-floor packager stays unchanged."""
    from randomizer.cave_journey import create_wfg_route,identity,initial_entry
    if output.exists():raise ValueError('use a fresh private WFG package')
    output=output.resolve();workspace=workspace.resolve()
    if not output.is_relative_to(workspace/'output'):raise ValueError('private output WFG package required')
    journey=create_wfg_route(seed,slot);output.mkdir(parents=True)
    files={};blueprints={}
    for index,spec in enumerate(journey['floors']):
        directory=output/f'floor-{index}';descriptor=spec['descriptor']
        checkpoint=initial_entry(descriptor,wire_schema=2 if index==0 else None)
        meta=stage(descriptor,assets,pod,exe,generator,directory,spec['salt'],checkpoint,species_banks)
        for name,digest in meta['files'].items():files[f'floor-{index}/{name}']=digest
        files[f'floor-{index}/package.json']=sha(directory/'package.json')
        names=('cave.json','layout.json','render.mod','collision.json',
               'assets/dataDir/courses/pikmin2room/room.mod',
               'assets/dataDir/stages/chal0/default.gen')
        for name in names:files[f'floor-{index}/{name}']=sha(directory/name)
        blueprints[str(index)]={name:files[f'floor-{index}/{name}'] for name in names if 'default.gen' not in name}
    for source,name in ((exe,'nectar.exe'),(generator,'cave-generator.exe')):shutil.copy2(source,output/name)
    for dll in exe.parent.glob('*.dll'):shutil.copy2(dll,output/dll.name)
    (output/'journey.json').write_text(json.dumps(journey,indent=2)+'\n')
    for path in output.iterdir():
        if path.is_file():files[path.name]=sha(path)
    meta=dict(schema=4,policy=journey['policy'],fingerprint=identity(journey),
        assets=str(assets.resolve()),pod=str(pod.resolve()),workspace=str(workspace),files=files,blueprints=blueprints,
        limitations=['Source White Flower Garden identity; original engineering acquisition geometry.',
                     'Full ordinary PW acquisition and route gameplay remain UNTESTED.'])
    (output/'package.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta


def stage_package(seed,slot,assets,pod,exe,generator,bundle,identity,output,workspace,species_banks=None,*,wfg_acquisition=False):
    banks=read_species_banks(species_banks,surface=True)  # fail before creating a partial runnable package
    if type(wfg_acquisition) is not bool:raise ValueError('WFG opt-in must be boolean')
    if wfg_acquisition:
        if set(banks)!={3,4}:raise ValueError('WFG route requires both Purple and White banks')
        stage_wfg_journey(seed,slot,assets,pod,exe,generator,output,workspace,species_banks)
    else:stage_journey(seed,slot,assets,pod,exe,generator,output,workspace)
    # Short connected approach: source ground rises50->80 at z1350->1240.
    # Shoreline220,1000 is separated by a ledge and needs a much longer route.
    surface=dict(position=ROUTE_START,health=1.,squad=[[1,0]]*20)
    if wfg_acquisition:
        _,inputs=stage_surface(assets,bundle,identity,output/'surface-blueprint',exe,surface,'0'*32,destination='forest_2/f_02')
    else:_,inputs=stage_surface(assets,bundle,identity,output/'surface-blueprint',exe,surface,'0'*32)
    run=output/'surface-blueprint/run'
    record=dict(schema=2 if wfg_acquisition else 1,bundle=str(bundle.resolve()),receipt_identity=identity,
                surface=surface,files={name:sha(run/name) for name in inputs},
                geometry={name:sha(run/name) for name in ('assets/dataDir/courses/p2tutorial/full.mod',
                    'assets/dataDir/courses/p2tutorial/full.water')})
    if species_banks:record['species_banks']=pin_species_banks(output,species_banks)
    if wfg_acquisition:
        record.update(profile='wfg-pw-acquisition-route-v1',first_destination='forest_2/f_02',
                      later_destination='forest_1',acquisition_index=0)
    (output/'route-package.json').write_text(json.dumps(record,indent=2)+'\n')
    launcher=Path(__file__).with_name('play_pikmin2_cave_route.py')
    (output/'PlayRoute.cmd').write_text('@echo off\npy -3.12 "'+str(launcher)+'" "'+str(output)+'"\npause\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','pod','exe','generator','bundle','output','workspace'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--identity',required=True);p.add_argument('--seed',default='1154');p.add_argument('--slot',default='Player1')
    p.add_argument('--purple-bank',type=Path);p.add_argument('--white-bank',type=Path)
    p.add_argument('--wfg-acquisition',action='store_true')
    a=p.parse_args();banks={s:path for s,path in ((3,a.purple_bank),(4,a.white_bank)) if path is not None}
    print(json.dumps(stage_package(a.seed,a.slot,a.assets,a.pod,a.exe,a.generator,bundle=a.bundle,identity=a.identity,output=a.output,workspace=a.workspace,species_banks=banks or None,wfg_acquisition=a.wfg_acquisition),indent=2))
