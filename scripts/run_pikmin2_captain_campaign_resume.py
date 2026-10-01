"""Bounded real native campaign save/resume; fixture setup is never a save file."""
from pathlib import Path
import argparse,hashlib,json,os,re,struct,sys,threading,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from randomizer.seed import generate,validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from preview_pikmin2_room import overlay,ensure_pikmin_squad

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--canonical-root',type=Path,required=True);p.add_argument('--session-root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--exe',type=Path,required=True);p.add_argument('--phase',choices=['save','resume1','resume2'],required=True);p.add_argument('--negative',choices=['active','inactive','null-state','missing-manager']);p.add_argument('--prepare-only',action='store_true');p.add_argument('--timeout',type=int,choices=[60,120],default=60);a=p.parse_args()
 canonical=a.canonical_root.resolve();sessiondir=a.session_root.resolve()
 assert sessiondir.is_relative_to(canonical/'output'),'Private output only'
 # This control/save fixture intentionally uses original P1 campaign geometry,
 # not imported-enemy or cave acceptance. Actual P2 captain code is opted in.
 if a.phase=='save':
  assert not sessiondir.exists(),'New save phase requires new session directory'
  sessiondir.mkdir(parents=True);m=generate('captain-save-1079','solo',starting_area='impact',starting_flarlic=2);validate(m)
  (sessiondir/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
 else:m=json.loads((sessiondir/'manifest.json').read_text(encoding='utf-8'));validate(m)
 session=Session(m,sessiondir);run=NativeRun(session);run.write_state(True)
 # Preserve production practice terrain/generators, append only a legal 20-red
 # fixture squad using the current helper (explicit campaign-stage equivalent).
 data=(a.assets/'dataDir/stages/practice/default.gen').read_bytes();assert data.count(b'ikip')==0
 staged=ensure_pikmin_squad(a.assets,data);assert staged.count(b'ikip')==20
 overrides={'dataDir/stages/practice/default.gen':staged};overlay(a.assets,run.directory/'assets',overrides)
 snapshot=lambda:{f.name:digest(f) for f in sorted((sessiondir/'campaign').glob('*.sav'))} if (sessiondir/'campaign').exists() else {}
 before=snapshot();assert len(before)==(0 if a.phase=='save' else 1)
 adoption=dict(wall_timeout_seconds=a.timeout,phase=a.phase,root_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),root_dirty=subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip(),root_worktree=str(ROOT),exe=str(a.exe.resolve()),exe_sha256=digest(a.exe),bootstrap_sha256=digest(run.bootstrap),expected_initial_field=20,geometry='unaltered P1 practice campaign terrain',fixture_generator_sha256=digest(run.directory/'assets/dataDir/stages/practice/default.gen'),saved_card_bytes_injected=False,day_or_population_state_injected=False,second_captain_binding='explicit environment on pre1080 producer; generated option is separate',before_cards=before)
 info=a.exe.resolve().parent/'BUILD_INFO.txt'
 if info.exists():adoption['CI_build_info']=dict(path=str(info),sha256=digest(info),text=info.read_text(encoding='utf-8'))
 (run.directory/'adoption-inputs.json').write_text(json.dumps(adoption,indent=2),encoding='utf-8')
 (sessiondir/(a.phase+'-run.json')).write_text(json.dumps(dict(directory=str(run.directory)),indent=2),encoding='utf-8')
 print(run.directory,flush=True)
 if a.prepare_only:return
 # Admission and bounded supervision come from the canonical workspace tools.
 adm=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"$o=Get-CimInstance Win32_OperatingSystem;$g=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'nectar|fixture.*exe'});@{ram=100*(1-$o.FreePhysicalMemory/$o.TotalVisibleMemorySize);games=$g.Count}|ConvertTo-Json"],text=True))
 assert adm['ram']<=90 and adm['games']<6,adm
 (run.directory/'admission.json').write_text(json.dumps(adm),encoding='utf-8')
 import importlib.util
 sys.path.insert(0,str(canonical/'scripts'))
 spec=importlib.util.spec_from_file_location('captain_guarded_runner',canonical/'scripts/run_pikmin2_fixture.py');guarded=importlib.util.module_from_spec(spec);spec.loader.exec_module(guarded)
 done=threading.Event();errors=[]
 def keepalive():
  try:
   while not done.wait(.1):run.poll();run.write_state(True)
  except Exception as e:errors.append(repr(e))
 thread=threading.Thread(target=keepalive);thread.start()
 args=['--randomizer-seed',str(run.bootstrap)];marker='PASS P2_CAPTAIN_CAMPAIGN_SAVE' if a.phase=='save' else 'PASS P2_CAPTAIN_CAMPAIGN_RESUME'
 if a.phase!='save':args.append('--resume-phase')
 if a.negative:args.append({'active':'--force-captain-down','inactive':'--force-inactive-down','null-state':'--force-null-state','missing-manager':'--force-missing-manager'}[a.negative])
 try:result=guarded.launch(a.exe,run.directory,args,[marker],a.timeout,a.exe.resolve().parent)
 finally:done.set();thread.join()
 assert not errors,errors
 run.poll() # consume the final flushed native journal before comparing rewards
 log=(run.directory/'native.log').read_text(errors='replace');after=snapshot()
 if a.negative:assert result['exit_code']==86 and result['captain_down'] and not result['passed'];return
 assert result['passed'],result
 assert run.handshaken,'actual production handshake required'
 if a.phase=='save':
  assert len(after)==1 and 'CAMPAIGN_SAVED generation=1' in log
  end=re.search(r'PASS P2_CAPTAIN_CAMPAIGN_SAVE day_before=(\d+) day_after=(\d+)',log);assert end and int(end[2])==int(end[1])+1
  facts=re.search(r'P2_SAVE_SCENE .*?live=(\d+) stored=(\d+)',log);assert facts
  baseline=dict(cards=after,day=int(end[2]),total=int(facts[1])+int(facts[2]),checked=sorted(session.data['checked']),inventory=dict(session.inventory))
  (sessiondir/'saved-observation.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
 else:
  baseline=json.loads((sessiondir/'saved-observation.json').read_text());assert before==after==baseline['cards'],'committed card mutated on resume'
  facts=re.search(r'P2_SAVE_SCENE phase=resume resumed=1 day=(\d+) live=(\d+) stored=(\d+)',log);assert facts
  assert sorted(session.data['checked'])==baseline['checked'] and dict(session.inventory)==baseline['inventory'],'duplicate or new reward on unchanged replay path'
  assert int(facts[1])==baseline['day'] and int(facts[2])+int(facts[3])==baseline['total'],'day/population did not conserve through actual card load'
 (run.directory/'phase-verified.json').write_text(json.dumps(dict(passed=True,result=result,before=before,after=after,baseline=baseline),indent=2),encoding='utf-8')
 print(json.dumps(result),flush=True)
if __name__=='__main__':main()
