"""Generate and run an isolated source-cargo acceptance fixture; no native source edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def instrument(source, value=100, weight=5, slots=10):
    if type(value) is not int or not 0<=value<=1000000 or type(weight) is not int or not 1<=weight<=1000 or type(slots) is not int or not 1<=slots<=128:
        raise ValueError('Invalid cargo expectations')
    replacements = {
      '    int frames=0,repairs=0;': '    int frames=0,repairs=0;\n    Pellet* sourceCargo=nullptr; bool seamEast=false,seamWest=false;',
      '            Pellet* target=pc_p2_preview_treasure();int count=0;Iterator p(pikiMgr);CI_LOOP(p){':
      f'''            Pellet* target=pc_p2_preview_treasure();sourceCargo=target;
            require(target && target->mConfig->mCarryMinPikis()=={weight} && target->mConfig->mCarryMaxPikis()=={slots},"source cargo carry settings");
            require(target->mSRT.t.x>595,"cargo must start beyond connector");
            std::printf("P2_SOURCE_CARGO_CONFIG value={value} weight={weight} slots={slots}\\n");
            int count=0;Iterator p(pikiMgr);CI_LOOP(p){{''',
      '        } else if(phase==2) {': '''        } else if(phase==2) {
            if(sourceCargo->mSRT.t.x<=595 && !seamEast){seamEast=true;std::puts("P2_SOURCE_CARGO_SEAM east");}
            if(sourceCargo->mSRT.t.x<=425 && !seamWest){require(seamEast,"cargo seam order");seamWest=true;std::puts("P2_SOURCE_CARGO_SEAM west");}''',
      '                if(pc_p2_preview_goal())require(pc_p2_preview_pokos()==180,"Citrus Lump must award 180 Pokos");':
      f'''                require(pc_p2_preview_goal() && pc_p2_preview_pokos()=={value},"source cargo value");
                require(seamEast && seamWest,"cargo did not traverse connector");
                require(pc_p2_preview_deliver(sourceCargo),"duplicate receipt hook refused");
                require(pc_p2_preview_pokos()=={value} && playerState->getCurrParts()==repairs,"duplicate credit or repairs changed");
                std::puts("P2_SOURCE_CARGO_PASS value={value} weight={weight} slots={slots} seams=2 duplicate_credit=0 repairs_unchanged=1");'''
    }
    for old,new in replacements.items():
        if source.count(old)!=1:raise ValueError('Native fixture framing changed: '+old[:60])
        source=source.replace(old,new)
    return source


def validate(log, receipt, value=100, weight=5, slots=10, catalog_id='juji_key_fc'):
    expected=f'P2_SOURCE_CARGO_PASS value={value} weight={weight} slots={slots} seams=2 duplicate_credit=0 repairs_unchanged=1'
    if expected not in log or 'PASS p2 second floor:' not in log:raise ValueError('Incomplete native acceptance')
    if receipt.strip()!=f'treasure={catalog_id} count=1 pokos={value}':raise ValueError('Wrong receipt identity/value')
    for new in (1,0):
        if f'P2_POD_RECEIPT id=treasure:{catalog_id} value={value} new={new} pokos={value} seeds=0' not in log:
            raise ValueError('Missing actual/duplicate receipt evidence')
    return dict(value=value,weight=weight,slots=slots,catalog_id=catalog_id,seams=2,duplicate_credit=0,repairs_unchanged=True)


def build(native, recipe_path, output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    source=native/'tools/preview_p2_room.cpp';raw=source.read_text()
    private=output/'source_cargo.cpp';private.write_text(instrument(raw))
    recipe=json.loads(recipe_path.read_text());commands={}
    for kind in ('compile','link'):
        args=[]
        for token in recipe[kind]:
            name=token.replace('\\','/').split('/')[-1]
            if name=='preview_p2_room.cpp':token=str(private)
            elif name=='preview_p2_room.obj':token=str(output/'source_cargo.obj')
            elif name=='preview_p2_room.exe':token=str(output/'source_cargo.exe')
            args.append(token)
        if kind=='compile':args.insert(1,'-I'+str((native/'tools').resolve()))
        commands[kind]=args
        env=dict(os.environ);env['PATH']=str(Path(args[0]).parent)+os.pathsep+env.get('PATH','')
        with (output/(kind+'.log')).open('w') as log:
            result=subprocess.run(args,cwd=recipe['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Private '+kind+' failed; see '+str(output/(kind+'.log')))
    (output/'build.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(raw.encode()).hexdigest(),commands=commands),indent=2))
    return output/'source_cargo.exe'


def run(exe, stage, runtime):
    if (stage/'treasure-receipt.txt').exists():raise ValueError('Use fresh private stage, receipt already exists')
    env=dict(os.environ);env['PATH']=str(runtime)+os.pathsep+env.get('PATH','');env['SDL_AUDIODRIVER']='dummy'
    with (stage/'source-cargo.log').open('w') as log:
        result=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    if result.returncode:raise RuntimeError('Native fixture exit '+str(result.returncode))
    evidence=validate((stage/'source-cargo.log').read_text(),(stage/'treasure-receipt.txt').read_text())
    evidence['exe_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
    evidence['log_sha256']=hashlib.sha256((stage/'source-cargo.log').read_bytes()).hexdigest()
    (stage/'source-cargo-acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stage',type=Path);p.add_argument('--runtime',type=Path,default=Path('C:/msys64/mingw64/bin'))
    a=p.parse_args();exe=build(a.native.resolve(),a.recipe,a.output);print(exe,flush=True)
    if a.stage:print(json.dumps(run(exe,a.stage.resolve(),a.runtime)),flush=True)
