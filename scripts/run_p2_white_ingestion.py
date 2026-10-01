"""Fresh ordinary White acquisition and natural adult ingestion acceptance."""
import argparse,hashlib,json,os,struct,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.preview_p2_white_acquisition import prepare
from scripts.preview_pikmin2_room import generator,records

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stage(a,run):
 prepare(a.assets,a.white,a.pod,a.room,run)
 gen=run/'assets/dataDir/stages/chal0/default.gen';data=gen.read_bytes()
 # Use the existing ordinary enemy generator framing, single actual Swallow actor.
 import re
 raw=generator(a.assets);starts=[m.start() for m in re.finditer(b'    0.0v',raw)]
 rows=[raw[s:(starts[i+1] if i+1<len(starts) else len(raw))] for i,s in enumerate(starts)]
 pred=bytearray(next(r for r in rows if r[16:48].rstrip(b'\0')==b'preview dwarf bulborb'))
 struct.pack_into('<I',pred,8,436207616);pred[16:48]=b'preview poison adult'.ljust(32,b'\0');pred[80]=4
 struct.pack_into('>6f',pred,48,200,0,-145,0,270,0)
 # Overlay files may hardlink source assets; write a replacement rather than modifying in place.
 gen.unlink();gen.write_bytes(data[:20]+struct.pack('>I',struct.unpack_from('>I',data,20)[0]+1)+data[24:]+pred)
 for name in ('p2-white-poison.txt','white-poison.json'):(run/name).write_bytes((a.poison/name).read_bytes())
 (run/'p2-cave-entry.txt').write_text('P2_CAVE_ENTRY_2\n'+uuid.uuid4().hex+'\n1 1 20\n'+'1 0\n'*20)
 return dict(generator_sha256=sha(gen),poison_sha256=sha(run/'p2-white-poison.txt'),predator_uid=436207616,predator_family='native P1 TEKI_Swallow adapter',presentation='native P1 adult; imported P2 adult presentation/AI/HP unclaimed',position=[200,0,-145],rotation=[0,270,0],placement='staged ordinary generator; no actor writes',initial='staged canonical 20 Red overlay with native ENTRY2 baseline restoration; natural starting supply unclaimed',controls='actual SDL P1 polling only',startup='movie skip/tutorial flags/audio dummy',positive_injections='none: no HP/species/attachment/callback/reward/budget/timer writes',source_exe_sha256=sha(a.exe),runner_sha256=sha(__file__),timeout_seconds=60)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('workspace','exe','assets','white','pod','room','poison'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--negative',action='store_true');a=p.parse_args();root=a.workspace.resolve();sys.path.insert(0,str(root/'scripts'))
 from run_pikmin2_fixture import launch
 for k in list(os.environ):
  if k.startswith(('P2_WHITE_','PIKMIN_CAVE_','PIKMIN_P2_','PIKMIN_RANDOMIZER_AUTOPLAY')):del os.environ[k]
 os.environ['PIKMIN_RANDOMIZER_AUTOPLAY']='0';os.environ['PIKMIN_P2_ROOM_WINDOW']='960x540'
 if a.negative:os.environ['P2_WHITE_INGESTION_FORCE_CAPTAIN_DOWN']='1'
 run=root/'output/white-ingestion'/('run-'+('negative-' if a.negative else 'positive-')+uuid.uuid4().hex[:10]);d=stage(a,run);(run/'disclosure.json').write_text(json.dumps(d,indent=2))
 marker='P2_FIXTURE_CAPTAIN_DOWN' if a.negative else 'P2_WHITE_INGESTION_PASS'
 result=launch(a.exe,run,['--experimental-pikmin2-room'],[marker],60);log=(run/'native.log').read_text(errors='replace')
 checks=dict(raw_exit=result.get('exit_code')==(86 if a.negative else 0),bounded=not result.get('timed_out'),marker=marker in log)
 if a.negative:checks['no_pass']='P2_WHITE_INGESTION_PASS' not in log
 else:checks.update(ordinary_pluck='P2_WHITE_INGESTION_PLUCKED' in log,natural_capture='P2_WHITE_INGESTION_CAPTURED' in log,production_poison=log.count('P2_WHITE_POISON_CONSUMED')==1 and 'damage=750.000' in log,guard='P2_FIXTURE_CAPTAIN_DOWN' not in log)
 report=dict(passed=all(checks.values()),checks=checks,result=result,full_campaign=False,outputs={f.name:sha(f) for f in run.iterdir() if f.is_file()});(run/'assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(run=str(run),assessment=report),indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
