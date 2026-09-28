"""Seven real native processes; SDL/confirmation/gameplay fixture injections explicit."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

from experimental import pikmin2_campaign as cave
from scripts import play_pikmin2_surface_loop as loop
from scripts.test_pikmin2_surface_native import executable_identity,expected_receipts


def build_apps(directory, recipe_path, object_base):
    directory.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    source=root/'scripts/pikmin2_manual_entrance.cpp'
    data=source.read_text();marker='int main(int argc,char**argv)'
    if data.count(marker)!=1:raise ValueError('Manual App extraction boundary changed')
    (directory/'manual-app.inc').write_text(data.split(marker)[0])
    # Freeze fixture bytes before a potentially long LTO link.
    fixture_source=root/'scripts/pikmin2_repeat_fixture.cpp'
    (directory/'fixture.cpp').write_bytes(fixture_source.read_bytes())
    base=json.loads(recipe_path.read_text());recipes={}
    ninja=(Path(base['cwd'])/'build.ninja').read_text()
    lines=[line for line in ninja.splitlines() if line.startswith('build bin/nectar.exe: ')]
    if len(lines)!=1:raise ValueError('Production executable target changed')
    objects=lines[0].split(' | ')[0].split()[3:]
    if not objects or any(not o.startswith('CMakeFiles/pikmin_pc.dir/') or not o.endswith('.obj') for o in objects):
        raise ValueError('Unexpected production object syntax')
    if sum(o.endswith('/pc_main.cpp.obj') for o in objects)!=1:raise ValueError('Missing production main object')
    env=dict(os.environ);env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    # LTO can inline the setter into settings, bypassing the private --wrap guard.
    # Compile unchanged settings privately without LTO so that call remains external.
    settings_source=root/'native/pc_port/settings/pc_settings.cpp'
    settings_compile=[str(settings_source) if a.endswith('pikmin2_manual_entrance.cpp') else
                      str(directory/'settings.obj') if a.endswith('manual.obj') else a for a in base['compile']]+['-fno-lto']
    recipes['settings_compile']=settings_compile
    with (directory/'settings-build.log').open('w') as log:
        subprocess.run(settings_compile,cwd=base['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    for name,cpp in [('manual',source),('fixture',directory/'fixture.cpp')]:
        recipe=dict(cwd=base['cwd'],object_base=object_base)
        recipe['compile']=[str(cpp) if a.endswith('pikmin2_manual_entrance.cpp') else str(directory/f'{name}.obj') if a.endswith('manual.obj') else a for a in base['compile']]
        recipe['compile']+=['-I'+str(directory),'-I'+str(root/'scripts')]
        recipe['link']=[str(directory/f'{name}.exe') if a.endswith('manual.exe') else
                        '-Wl,--out-implib,'+str(directory/f'{name}.dll.a') if a.startswith('-Wl,--out-implib,') else a
                        for a in base['link'] if not (a.startswith('CMakeFiles/pikmin_pc.dir/') and a.endswith('.obj')) and not a.endswith('manual.obj')]
        recipe['link'][1:1]=[str(directory/f'{name}.obj') if o.endswith('/pc_main.cpp.obj') else
                             str(directory/'settings.obj') if o.endswith('/settings/pc_settings.cpp.obj') else o for o in objects]
        recipe['link'].append('-flto=4')
        if name=='fixture':recipe['link'].append('-Wl,--wrap=SDL_ShowMessageBox')
        recipes[name]=recipe
        (directory/'commands.json').write_text(json.dumps(recipes,indent=2))
        with (directory/f'{name}-build.log').open('w') as log:
            for step in ('compile','link'):
                subprocess.run(recipe[step],cwd=recipe['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    (directory/'sources.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (source,settings_source,fixture_source,directory/'fixture.cpp',directory/'manual-app.inc')},indent=2))


class RepeatProcess:
    def __init__(self,directory,timeout):
        if not 1<=timeout<=300:raise ValueError('Timeout must be1..300 seconds')
        self.directory,self.timeout=directory,timeout
        self.surface_count=0;self.cave_count=0;self.runs=[]

    def __call__(self,argv,*,cwd,**kwargs):
        cwd=Path(cwd);surface=(cwd/'manual-entrance.txt').exists()
        if surface:
            self.surface_count+=1;visit=self.surface_count;kind='surface'
            state=json.loads((self.directory/'session/surface-ledger.json').read_text())
            position=state['surface']['position']
        else:
            visit=self.cave_count//2+1;self.cave_count+=1;kind='cave';position=[0,0,0]
        if visit>3 or (kind=='cave' and visit>2):raise ValueError('Unexpected extra native visit')
        pokos=sum(cave.read_ledger(cwd/'p2-economy.txt').values())
        (cwd/'repeat-fixture.txt').write_text(f'{kind} {visit} {pokos} '+ ' '.join(map(str,position))+'\n')
        env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
        result=subprocess.run(argv,cwd=cwd,timeout=self.timeout,env=env,**kwargs)
        record=dict(kind=kind,visit=visit,path=str(cwd),exit=result.returncode,restored_pokos=pokos)
        self.runs.append(record)
        (self.directory/'native-runs.json').write_text(json.dumps(self.runs,indent=2))
        text=(cwd/'native.log').read_text(errors='replace')
        if result.returncode not in (0,42) or 'P2_REPEAT_RESTORE' not in text:
            raise RuntimeError(f'Native repeat fixture failed: {cwd}')
        if result.returncode==42 and ('P2_REPEAT_F6_INJECTED' not in text or 'P2_REPEAT_CONFIRM_INJECTED' not in text):
            raise RuntimeError('Transition did not use injected SDL event/confirmation path')
        return result


def run_test(args):
    args.output.mkdir(parents=True,exist_ok=False)
    provenance=dict(manual=executable_identity(args.manual_exe),fixture=executable_identity(args.fixture_exe))
    (args.output/'fixture-provenance.json').write_text(json.dumps(provenance,indent=2))
    args.surface_exe=args.fixture_exe;args.cave_exe=args.fixture_exe
    process=RepeatProcess(args.output,args.timeout)
    final=loop.play(args,process)
    assert final['phase']=='surface' and final['revision']==8
    assert final['surface']['receipts']==expected_receipts(args.roster)
    assert Counter(p['species'] for p in final['surface']['squad'])=={'red':9,'purple':10}
    assert final['surface']['health']==.5
    assert [r['exit'] for r in process.runs]==[42,42,42,42,42,42,0]
    assert process.runs[3]['restored_pokos']==process.runs[6]['restored_pokos']==sum(expected_receipts(args.roster).values())
    report=dict(final=final,runs=process.runs,provenance=provenance,physical_input_tested=False,
                injected=['SDL F6','confirmation answer','captain movement','casualty/maturity/health/Purple changes',
                          'enemy removal','native delivery hooks','final surface exit'],full_world_restore=False)
    (args.output/'result.json').write_text(json.dumps(report,indent=2))
    print('PASS seven native processes / two visits / no duplicate cumulative receipts')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','manual-exe','fixture-exe','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('transitions','snow','roster','transition-assets'):p.add_argument('--'+name,type=Path)
    p.add_argument('--timeout',type=int,default=120);args=p.parse_args()
    for name,value in vars(args).items():
        if isinstance(value,Path):setattr(args,name,value.resolve())
    run_test(args)
