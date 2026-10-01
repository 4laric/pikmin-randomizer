"""Ordinary White acquisition followed by native checkpoint and fresh restore."""
import argparse, hashlib, json, math, os, re, sys, uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.preview_p2_white_acquisition import prepare

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def transfer(path):
 words=Path(path).read_text().split()
 if len(words)!=45 or words[0]!='P2_CAVE_TRANSFER_2' or not re.fullmatch('[0-9a-f]{32}',words[1]):raise ValueError('transfer header/length')
 floor=int(words[2]);health=float(words[3]);count=int(words[4]);records=[tuple(map(int,words[i:i+2])) for i in range(5,len(words),2)]
 if floor!=1 or not math.isfinite(health) or not 0<health<=1 or count!=20 or records.count((1,0))!=19 or records.count((4,0))!=1:raise ValueError('transfer species/maturity/health/count')
 return words,records

def accepted_producer(directory):
 directory=Path(directory);report=json.loads((directory/'assessment.json').read_text())
 if report.get('mode')!='producer' or report.get('passed') is not True:raise ValueError('producer not accepted')
 for name,digest in report['outputs'].items():
  if Path(name).name!=name or sha(directory/name)!=digest:raise ValueError('producer hash mismatch: '+name)
 words,records=transfer(directory/'p2-cave-transfer.txt')
 if words[1]!=json.loads((directory/'disclosure.json').read_text())['entry_token']:raise ValueError('transfer token mismatch')
 return words,records

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('workspace','exe','assets','white','pod','room'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--mode',choices=('producer','consumer','negative'),default='producer');p.add_argument('--producer',type=Path)
 a=p.parse_args();root=a.workspace.resolve();sys.path.insert(0,str(root/'scripts'))
 from run_pikmin2_fixture import launch
 # Refuse unaccepted/tampered input before staging or launching any process.
 restored=accepted_producer(a.producer) if a.mode=='consumer' and a.producer else None
 if a.mode=='consumer' and restored is None:raise ValueError('--producer required')
 run=root/'output/white-checkpoint'/('run-'+a.mode+'-'+uuid.uuid4().hex[:10])
 for key in list(os.environ):
  if key.startswith(('P2_WHITE_','PIKMIN_CAVE_','PIKMIN_P2_','PIKMIN_RANDOMIZER_AUTOPLAY')):del os.environ[key]
 os.environ['PIKMIN_RANDOMIZER_AUTOPLAY']='0';os.environ['PIKMIN_P2_ROOM_WINDOW']='960x540'
 if a.mode=='consumer':os.environ['P2_WHITE_CHECKPOINT_RESTORE']='1'
 if a.mode=='negative':os.environ['P2_WHITE_CHECKPOINT_FORCE_CAPTAIN_DOWN']='1'
 prepare(a.assets,a.white,a.pod,a.room,run)
 token=restored[0][1] if restored else uuid.uuid4().hex
 health=restored[0][3] if restored else '1'
 records=restored[1] if restored else [(1,0)]*20
 (run/'p2-cave-entry.txt').write_text('P2_CAVE_ENTRY_2\n'+token+'\n1 '+health+' 20\n'+''.join(f'{s} {m}\n' for s,m in records))
 disclosure=dict(mode=a.mode,entry_token=token,producer=str(a.producer) if restored else None,starting='fresh current 20-body generator overlay',input='actual SDL virtual P1/native polling; consumer uses native checkpoint restoration',movies='skipped',tutorial_flags='suppressed',confirmation='bypassed through native checkpoint(false)',squad_checkpoint='global survivors; full-squad arrival untested',bud_budget_persistence=False,ship_day_save_campaign_accepted=False,timeout_seconds=60,runner_sha256=sha(__file__),exe_sha256=sha(a.exe))
 (run/'disclosure.json').write_text(json.dumps(disclosure,indent=2))
 marker={'producer':'P2_WHITE_CHECKPOINT_COMMITTED','consumer':'P2_WHITE_CHECKPOINT_RESTORE_PASS','negative':'P2_FIXTURE_CAPTAIN_DOWN'}[a.mode]
 result=launch(a.exe,run,['--experimental-pikmin2-room'],[marker],60)
 log=(run/'native.log').read_text(errors='replace');expected={'producer':42,'consumer':0,'negative':86}[a.mode]
 checks=dict(exit=result.get('exit_code')==expected,bounded=not result.get('timed_out') and result.get('timeout_seconds')==60,marker=marker in log)
 if a.mode=='negative':checks['no_success']='P2_WHITE_CHECKPOINT_COMMITTED' not in log and 'P2_WHITE_CHECKPOINT_RESTORE_PASS' not in log
 else:checks['captain_safe']=not result.get('captain_down')
 if a.mode=='producer':
  try:words,_=transfer(run/'p2-cave-transfer.txt');checks['native_transfer']=words[1]==token
  except (ValueError,OSError):checks['native_transfer']=False
 report=dict(mode=a.mode,passed=all(checks.values()),checks=checks,raw_result=result,full_campaign_accepted=False,outputs={f.name:sha(f) for f in run.iterdir() if f.is_file()})
 (run/'assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(run=str(run),assessment=report),indent=2))
 return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
