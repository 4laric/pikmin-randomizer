"""Compare natural cargo behavior with/without optional source visuals."""
import argparse,json,os,re,subprocess
from pathlib import Path
from experimental.pikmin2_breadbug_arena import prepare
from experimental.pikmin2_breadbug_cargo_install import install
from scripts.test_pikmin2_surface_native import executable_identity
from scripts.test_pikmin2_breadbug_cargo_native import evidence

def animation_evidence(text,enabled):
    states={int(s) for s in re.findall(r'P2_BREADBUG_CARGO_VISUAL generator=186081 state=(\d+)',text)}
    frames=re.findall(r'P2_BREADBUG_ANIMATION_FRAME state=(\d+) counter=([-\d.]+) kind=(-?\d+) source=([-\d.]+)',text)
    if 'P2_BREADBUG_ANIMATION_PAUSE_PASS' not in text:raise ValueError('Missing pause assertion')
    if enabled and not {5,6,8}.issubset(states):raise ValueError('Missing actual native cargo draw states')
    if not enabled and states:raise ValueError('Absent bank changed legacy rendering')
    if enabled:
        for state in (5,6,8):
            values={float(frame) for s,_,kind,frame in frames if int(s)==state and int(kind)==(1 if state==8 else 0)}
            if len(values)<2:raise ValueError('Source phase did not advance')
    return dict(render_states=sorted(states),phase_rows=len(frames),pause='injected engine pause, 59 unchanged-counter checks; not physical menu QA')

def run(args):
    args.output.mkdir(parents=True,exist_ok=False);exe=executable_identity(args.exe);results={}
    env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    for label,enabled in [('baseline',False),('cargo_bank',True)]:
        base=args.output/label;base.mkdir();stage=prepare(args.assets,args.profile,base)
        if enabled:install(args.bank,args.profile,stage)
        with (stage/'host.log').open('w') as out:
            native=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout)
        text=(stage/'host.log').read_text(errors='replace')
        if native.returncode:raise RuntimeError(f'{label} exit {native.returncode}: {stage}')
        cargo=evidence(text)
        if not cargo['complete']:raise ValueError(f'{label}: incomplete natural interaction')
        results[label]=dict(directory=str(stage),cargo=cargo,animation=animation_evidence(text,enabled))
    result=dict(executable=exe,runs=results,scope='same build; unforced P1 cargo and optional visual comparison, no exact deterministic trajectory claim')
    (args.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('assets','profile','bank','exe','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--timeout',type=int,default=100);a=p.parse_args()
    for k,v in vars(a).items():
        if isinstance(v,Path):setattr(a,k,v.resolve())
    run(a)
