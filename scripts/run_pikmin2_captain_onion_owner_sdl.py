"""Bounded real native campaign save/resume; fixture setup is never a save file."""
from pathlib import Path
import argparse,hashlib,json,os,re,struct,sys,threading,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from randomizer.seed import generate,validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from preview_pikmin2_room import overlay

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def runtime_dependencies(exe,runtime_directory=None):
 runtime_dir=runtime_directory.resolve(strict=True) if runtime_directory else Path('C:/msys64/mingw64/bin')
 runtime_hashes={name:digest(runtime_dir/name) for name in ('libstdc++-6.dll','libgcc_s_seh-1.dll','libwinpthread-1.dll')}
 if runtime_directory:
  runtime_hashes['SDL2.dll']=digest(runtime_dir/'SDL2.dll')
  for name,sha in runtime_hashes.items():
   local=exe.resolve().parent/name
   if local.exists() and digest(local)!=sha:raise ValueError(f'Conflicting executable-local runtime DLL: {local}')
 return runtime_dir,runtime_hashes

def main():
 p=argparse.ArgumentParser();p.add_argument('--canonical-root',type=Path,required=True);p.add_argument('--session-root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--exe',type=Path,required=True);p.add_argument('--phase',choices=['save','resume1','resume2'],required=True);p.add_argument('--negative',choices=['active','inactive','null-state','missing-manager']);p.add_argument('--runtime-dir',type=Path,help='Verified runtime DLL directory; use the matching CI artifact directory for packaged fixtures');p.add_argument('--prepare-only',action='store_true');p.add_argument('--timeout',type=int,choices=[60],default=60);a=p.parse_args()
 canonical=a.canonical_root.resolve();sessiondir=a.session_root.resolve()
 runtime_dir,runtime_hashes=runtime_dependencies(a.exe,a.runtime_dir)
 removed={k:os.environ.pop(k) for k in list(os.environ) if k.startswith(('PIKMIN_','P2_','COOP_'))}
 os.environ['PIKMIN_RANDOMIZER_AUTOPLAY']='0'
 os.environ['PIKMIN_RANDOMIZER_TEST_BACKGROUND']='1'  # Inherit into CRT getenv before native startup (SDL_setenv alone is insufficient on this Windows runtime).
 os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']='1'
 os.environ['PIKMIN_P2_ROOM_WINDOW']='960x540'
 assert sessiondir.is_relative_to(canonical/'output'),'Private output only'
 # This control/save fixture intentionally uses original P1 campaign geometry,
 # not imported-enemy or cave acceptance. Actual P2 captain code is opted in.
 if a.phase=='save':
  assert not sessiondir.exists(),'New save phase requires new session directory'
  sessiondir.mkdir(parents=True);m=generate('captain-onion-owner-1166','solo',starting_area='impact',starting_flarlic=2,p2_enemies=True,p2_species=[2],p2_second_captain=True);validate(m)
  (sessiondir/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
 else:
  m=json.loads((sessiondir/'manifest.json').read_text(encoding='utf-8'));validate(m)
  if a.timeout==60:assert json.loads((sessiondir/'saved-observation.json').read_text()).get('acceptance') is True,'acceptance resume requires an accepted60-second save'
 session=Session(m,sessiondir);run=NativeRun(session);run.write_state(True)
 assert m.get("p2_second_captain") is True and "CAPTAINS 2\n" in run.bootstrap.read_text(),"generated captain choice required"
 # Original campaign assets in every phase. Production TEST_BACKGROUND fresh
 # startup and the disclosed native resume fixture withdraw20 from real stock.
 data=(a.assets/'dataDir/stages/practice/default.gen').read_bytes();assert data.count(b'ikip')==0
 expected_field=20
 overlay(a.assets,run.directory/'assets',{})
 snapshot=lambda:{f.name:digest(f) for f in sorted((sessiondir/'campaign').glob('*.sav'))} if (sessiondir/'campaign').exists() else {}
 before=snapshot();assert len(before)==(0 if a.phase=='save' else 1)
 adoption=dict(diagnostic=a.timeout!=60,acceptance_eligible=a.timeout==60,wall_timeout_seconds=a.timeout,phase=a.phase,root_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),root_dirty=subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip(),root_worktree=str(ROOT),exe=str(a.exe.resolve()),exe_sha256=digest(a.exe),bootstrap_sha256=digest(run.bootstrap),expected_initial_field=expected_field,starting_baseline="20live from actual Onion withdrawal; no appended generators",geometry='unaltered P1 practice campaign terrain',fixture_generator_sha256=digest(run.directory/'assets/dataDir/stages/practice/1.gen'),default_generator_sha256=digest(run.directory/'assets/dataDir/stages/practice/default.gen'),fixture_schedule='identical original generators everyphase; actual production stock withdrawal supplies20live',saved_card_bytes_injected=False,day_or_population_state_injected=False,second_captain_binding='generated manifest p2_second_captain=True and CAPTAINS 2 bootstrap; native randomizer ignores ambient opt-in',before_cards=before)
 adoption['runtime_directory']=str(runtime_dir)
 adoption['runtime_dlls_sha256']=runtime_hashes
 info=a.exe.resolve().parent/'BUILD_INFO.txt'
 if info.exists():adoption['CI_build_info']=dict(path=str(info),sha256=digest(info),text=info.read_text(encoding='utf-8'))
 (run.directory/'adoption-inputs.json').write_text(json.dumps(adoption,indent=2),encoding='utf-8')
 (sessiondir/(a.phase+'-run.json')).write_text(json.dumps(dict(directory=str(run.directory)),indent=2),encoding='utf-8')
 print(run.directory,flush=True)
 if a.prepare_only:return
 # Admission and bounded supervision come from the canonical workspace tools.
 adm=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"$o=Get-CimInstance Win32_OperatingSystem;$g=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'nectar|fixture.*exe'});@{ram=100*(1-$o.FreePhysicalMemory/$o.TotalVisibleMemorySize);games=$g.Count}|ConvertTo-Json"],text=True))
 assert adm['ram']<=90 and adm['games']<6,adm
 (run.directory/'test-environment.json').write_text(json.dumps(dict(removed=removed,effective={k:v for k,v in os.environ.items() if k.startswith(('PIKMIN_','P2_','SDL_JOYSTICK'))}),indent=2))
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
 args=['--randomizer-seed',str(run.bootstrap)];marker='PASS P2_CAPTAIN_ONION_OWNER_SAVE' if a.phase=='save' else 'PASS P2_CAPTAIN_ONION_OWNER_RESUME'
 if a.phase!='save':args.append('--resume-phase')
 if a.negative:args.append({'active':'--force-captain-down','inactive':'--force-inactive-down','null-state':'--force-null-state','missing-manager':'--force-missing-manager'}[a.negative])
 try:result=guarded.launch(a.exe,run.directory,args,[marker],a.timeout,toolchain=runtime_dir)
 finally:done.set();thread.join()
 assert not errors,errors
 assert result.get('launched',True),result  # Preserve preflight failure before inspecting an absent native log.
 run.poll() # consume the final flushed native journal before comparing rewards
 log=(run.directory/'native.log').read_text(errors='replace');after=snapshot()
 if a.negative:assert result['exit_code']==86 and result['captain_down'] and not result['passed'];return
 assert result['passed'],result
 for stage in ('withdraw_complete','switched_to0','switched_back1','whistle1','before_sunset_or_resume_exit'):
  assert f'P2_ONION_OWNER stage={stage} owner0=0 owner1=20 plate0=0 plate1=20 live=20 stored=0 input_player=1 switched_captain=1' in log,stage
 assert run.handshaken,'actual production handshake required'
 if a.phase=='save':
  assert len(after)==1 and 'CAMPAIGN_SAVED generation=1' in log
  end=re.search(r'PASS P2_CAPTAIN_ONION_OWNER_SAVE day_before=(\d+) day_after=(\d+)',log);assert end and int(end[2])==int(end[1])+1
  facts=re.search(r'P2_SAVE_SCENE .*?live=(\d+) stored=(\d+)',log);assert facts
  baseline=dict(acceptance=a.timeout==60,save_wall_timeout_seconds=a.timeout,cards=after,day=int(end[2]),total=int(facts[1])+int(facts[2]),checked=sorted(session.data['checked']),inventory=dict(session.inventory))
  (sessiondir/'saved-observation.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
 else:
  baseline=json.loads((sessiondir/'saved-observation.json').read_text());assert before==after==baseline['cards'],'committed card mutated on resume'
  facts=re.search(r'P2_SAVE_SCENE phase=resume resumed=1 day=(\d+) live=(\d+) stored=(\d+)',log);assert facts
  assert sorted(session.data['checked'])==baseline['checked'] and dict(session.inventory)==baseline['inventory'],'duplicate or new reward on unchanged replay path'
  assert int(facts[1])==baseline['day'] and int(facts[2])+int(facts[3])==baseline['total'],'day/population did not conserve through actual card load'
 (run.directory/'phase-verified.json').write_text(json.dumps(dict(passed=True,diagnostic=a.timeout!=60,acceptance=a.timeout==60,result=result,before=before,after=after,baseline=baseline),indent=2),encoding='utf-8')
 print(json.dumps(result),flush=True)
if __name__=='__main__':main()
