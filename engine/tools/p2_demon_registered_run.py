"""Run the frozen registered captain fixture in separate private sessions."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path

def record(p):
    p=p.resolve(); return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
def main():
    parser=argparse.ArgumentParser()
    for name in ('root','assets','room','fixture','output'): parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args(); exe=a.fixture/'fixture.exe'; provenance=a.fixture/'provenance.json'
    data=json.loads(provenance.read_text()); actual=record(exe)
    expected=next(v for k,v in data['artifacts'].items() if Path(k).name=='fixture.exe')
    if data['status']!='built' or actual['sha256']!=expected['sha256']: raise ValueError('invalid executable provenance')
    helper=a.root/'scripts/preview_pikmin2_room.py'
    spec=importlib.util.spec_from_file_location('preview',helper); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    results=[]
    for mode in ('positive','interrupt','reset','rejected','external','flick','fatal','capacity','direct','handoff_walk','handoff_flick','handoff_geyzer','handoff_bury','handoff_pressed','stage_exit'):
        run=m.prepare(a.assets.resolve(),a.room.resolve(),a.output.resolve())
        env=dict(os.environ,DEMON_FIXTURE_MODE=mode)
        result={'mode':mode,'fixture':actual,'provenance':record(provenance),'runner':record(Path(__file__)),'helper':record(helper),
                'room':{n:record(a.room/n) for n in ('room.mod','room.ini','treasure.mod')},'status':'failed'}
        try:
            command=[str(exe.resolve()),'--experimental-pikmin2-room'];result['command']=command
            r=subprocess.run(command,cwd=run,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=75)
            (run/'stdout.log').write_text(r.stdout,encoding='utf8');(run/'stderr.log').write_text(r.stderr,encoding='utf8')
            result.update(returncode=r.returncode,stdout=record(run/'stdout.log'),stderr=record(run/'stderr.log'))
            if r.returncode==0 and f'PASS DEMON_REGISTERED mode={mode} ' in r.stdout: result['status']='passed_scoped_runtime'
        except Exception as e: result['error']=str(e)
        (run/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
        print(mode, result['status'],run,flush=True);results.append(result['status']=='passed_scoped_runtime')
    return 0 if all(results) else 1
if __name__=='__main__':raise SystemExit(main())
