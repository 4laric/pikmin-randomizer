"""Run the private original P1 Breadbug proxy arena: natural movement, reset,
re-entry rebind and injected death/cleanup. No P2 contest/carry claim."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from experimental.pikmin2_breadbug_arena import prepare,POSITIONS,IDS
from scripts import build_pikmin2_fixture as builder
from scripts.test_pikmin2_surface_native import executable_identity

ROOT=Path(__file__).resolve().parent.parent
PREFIX=ROOT/'output/p2-lifecycle-batch/breadbug-actor-runtime-build/room-prefix.inc'

def build(native,build_dir,output,head,prefix):
    native,build_dir,output=native.resolve(),build_dir.resolve(),output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    fixture=output/'fixture.cpp';fixture.write_text((ROOT/'scripts/pikmin2_breadbug_actor_fixture.cpp').read_text())
    shutil.copy2(prefix,output/'room-prefix.inc')
    record=builder.build_fixture(build_dir,native,fixture,output/'baseline',head)
    link=list(record['commands'][-1]);link[builder.option_index(link,'-o')]=str(output/'fixture.exe')
    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''))
    code,text=builder.run(link,build_dir,env);(output/'fixture-link.log').write_text(text)
    if code:raise RuntimeError('fixture link failed')
    return output/'fixture.exe',builder.snapshot([output/'fixture.exe'])

def validate(text):
    rows=re.findall(r'P2_BREADBUG_ACTOR_READY generator=(\d+) native_type=(\d+) xyz=([-\d.]+),([-\d.]+),([-\d.]+)',text)
    if not rows:raise ValueError('Expected at least one opted-in Breadbug')
    identity,kind,*xyz=rows[0]
    if int(identity)!=IDS[0] or int(kind)!=8 or any(abs(float(a)-b)>.1 for a,b in zip(xyz,POSITIONS[0])):raise ValueError('Full native birth identity/XYZ mismatch')
    if 'P2_BREADBUG_ACTOR_DRAW' not in text or 'PASS P2_BREADBUG_ACTOR_ARENA' not in text:raise ValueError('Missing live visual/movement/reset evidence')
    if 'P2_BREADBUG_ACTOR_REENTRY' not in text:raise ValueError('Missing manager re-entry evidence')
    if 'P2_BREADBUG_ACTOR_KILL' not in text or 'P2_BREADBUG_ACTOR_DEATH ' not in text:raise ValueError('Missing injected death/cleanup evidence')
    if 'Experimental preview window set to 960x540 windowed and centered' not in text:raise ValueError('Missing 960x540 centred window evidence')
    movement=re.findall(r'P2_BREADBUG_ARENA_MOVE frame=(\d+) displacement=([\d.]+) moving=(\d+)',text)
    if not movement or max(float(r[1]) for r in movement)<=15 or max(int(r[2]) for r in movement)<15:raise ValueError('Insufficient natural movement')
    corpse=int(re.search(r'P2_BREADBUG_ACTOR_DEATH corpse=(\d+)',text).group(1))
    return dict(identity=int(identity),birth_xyz=list(map(float,xyz)),max_displacement=max(float(r[1]) for r in movement),moving_frames=max(int(r[2]) for r in movement),reentry=True,injected_death=True,corpse=corpse)

def run(args):
    if args.exe is None:
        exe,identity=build(args.native,args.build_dir,args.output/'build',args.head,args.prefix)
    else:
        exe=args.exe;identity=executable_identity(args.exe)
    directory=prepare(args.assets,args.profile,args.output)
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PIKMIN_P2_ROOM_WINDOW='960x540');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    with (directory/'host.log').open('w') as out:
        result=subprocess.run([str(exe),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout)
    if result.returncode:raise RuntimeError(f'Native arena exit{result.returncode}: {directory}')
    evidence=validate((directory/'host.log').read_text(errors='replace'))
    report=dict(executable=identity,directory=str(directory),evidence=evidence,behavior='P1 Collec proxy; natural movement + manager reset/re-entry + injected death cleanup; no P2 corpse pellet, FSM/contest/carry')
    (args.output/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','profile','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--exe',type=Path);p.add_argument('--native',type=Path);p.add_argument('--build-dir',type=Path);p.add_argument('--head')
    p.add_argument('--prefix',type=Path,default=ROOT/'output/p2-lifecycle-batch/breadbug-actor-runtime-build/room-prefix.inc')
    p.add_argument('--timeout',type=int,default=120);a=p.parse_args()
    for k,v in vars(a).items():
        if isinstance(v,Path):setattr(a,k,v.resolve())
    if a.exe is None and not (a.native and a.build_dir and a.head):p.error('either --exe or --native/--build-dir/--head required')
    if a.exe is None and not re.fullmatch(r'[0-9a-f]{40}',a.head):p.error('invalid --head')
    if not 1<=a.timeout<=180:p.error('timeout must be1..180')
    run(a)
