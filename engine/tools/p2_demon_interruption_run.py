"""Run a provenance-checked private real-captain Demon drop fixture."""
import argparse
import json
import subprocess
from pathlib import Path
from p2_groink_volley_run import fixture_provenance, load_preview_prepare, file_record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','assets','room','fixture','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    prov,_,exe,_=fixture_provenance(a.fixture.resolve())
    run=load_preview_prepare(a.root.resolve())(a.assets.resolve(),a.room.resolve(),a.output.resolve())
    record={'status':'failed','fixture':file_record(exe),'provenance':file_record(prov),
            'runner':file_record(Path(__file__).resolve()),'preview_helper':file_record(a.root.resolve()/'scripts/preview_pikmin2_room.py'),
            'room_inputs':{n:file_record(a.room/n) for n in ('room.mod','room.ini','treasure.mod')},
            'limitations':['Injected drop entry; no enemy capture','Actor-local fixture state','P1 Attack receiver, not P2 damage fidelity','Production reset only; no actual destroy/rebirth or owner actor','Stale callback probes are synthetic']}
    command=[str(exe),'--experimental-pikmin2-room']; record['command']=command
    try:
        r=subprocess.run(command,cwd=run,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=75)
        (run/'stdout.log').write_text(r.stdout,encoding='utf-8'); (run/'stderr.log').write_text(r.stderr,encoding='utf-8')
        record['returncode']=r.returncode
        record['stdout']=file_record(run/'stdout.log'); record['stderr']=file_record(run/'stderr.log')
        markers=[f'DEMON_INTERRUPT_CANCEL scenario={i}' for i in range(4)]+['PASS DEMON_DROP_INTERRUPTION']
        if r.returncode==0 and all(m in r.stdout for m in markers): record['status']='passed_scoped_native_fixture'
    except Exception as error: record['error']=str(error)
    (run/'verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(run/'verification.json')
    return 0 if record['status']=='passed_scoped_native_fixture' else 1
if __name__=='__main__': raise SystemExit(main())
