"""Bounded real native campaign save/resume; fixture setup is never a save file."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,os,re,struct,sys,threading,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from randomizer.seed import generate,validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from preview_pikmin2_room import overlay
from fixture_platform import is_windows, runtime_dependencies, runtime_evidence
from blank_card_preflight import verify_prepared, inventory as blank_inventory
import run_pikmin2_fixture as guarded

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--canonical-root',type=Path,required=True);p.add_argument('--session-root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--exe',type=Path,required=True);p.add_argument('--phase',choices=['save','resume1','resume2'],required=True);p.add_argument('--negative',choices=['active','inactive','null-state','missing-manager']);p.add_argument('--runtime-dir',type=Path,help='Verified runtime DLL directory; use the matching CI artifact directory for packaged fixtures');p.add_argument('--prepare-only',action='store_true');p.add_argument('--prepared-card',type=Path,help='Accepted ordinary native blank-card initialization receipt; positive SAVE only');p.add_argument('--timeout',type=int,choices=[60],default=60);a=p.parse_args()
 canonical=a.canonical_root.resolve();sessiondir=a.session_root.resolve()
 if a.prepared_card and (a.phase!='save' or a.negative or a.prepare_only):raise ValueError('Prepared card is for an actual positive SAVE only')
 if canonical!=ROOT.resolve():raise ValueError('Runner must use its own pinned root checkout')
 runtime_dir,runtime_hashes=runtime_dependencies(a.exe,a.runtime_dir) if is_windows() else (None,{})
 removed={k:os.environ.pop(k) for k in list(os.environ) if k.startswith(('PIKMIN_','P2_','COOP_'))}
 os.environ['PIKMIN_RANDOMIZER_AUTOPLAY']='0'
 os.environ['PIKMIN_RANDOMIZER_TEST_BACKGROUND']='1'  # Inherit into CRT getenv before native startup (SDL_setenv alone is insufficient on this Windows runtime).
 if a.phase=='save':os.environ['PIKMIN_RANDOMIZER_MANUAL_START']='1'  # Existing production stock-held start, ordinary UI withdraws the20.
 os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']='1'
 os.environ['PIKMIN_P2_ROOM_WINDOW']='960x540'
 assert sessiondir.is_relative_to(canonical/'output'),'Private output only'
 # This control/save fixture intentionally uses original P1 campaign geometry,
 # not imported-enemy or cave acceptance. Actual P2 captain code is opted in.
 if a.phase=='save':
  if a.prepared_card:
   prepared=verify_prepared(a.canonical_root,a.session_root,a.prepared_card)
   with (sessiondir/'prepared-card-consumed.json').open('x',encoding='utf-8') as f:json.dump(dict(receipt_sha256=digest(a.prepared_card),native_blank_inventory=prepared['inventory'],retry=False),f,indent=2)
  else:
   assert not sessiondir.exists(),'New save phase requires new session directory'
   sessiondir.mkdir(parents=True)
  m=generate('captain-onion-owner-1166','solo',starting_area='impact',starting_flarlic=2,p2_enemies=True,p2_species=[2],p2_second_captain=True);validate(m)
  (sessiondir/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
 else:
  m=json.loads((sessiondir/'manifest.json').read_text(encoding='utf-8'));validate(m)
  if a.timeout==60:assert json.loads((sessiondir/'saved-observation.json').read_text()).get('acceptance') is True,'acceptance resume requires an accepted60-second save'
 session=Session(m,sessiondir);run=NativeRun(session);run.write_state(True)
 assert m.get("p2_second_captain") is True and "CAPTAINS 2\n" in run.bootstrap.read_text(),"generated captain choice required"
 # Original campaign assets in every phase. Fresh production MANUAL_START
 # holds20stock; ordinary captain0 UI withdraws them after readiness. Resume
 # uses the existing ordinary captain1 Onion UI path, with no startup recruitment.
 data=(a.assets/'dataDir/stages/practice/default.gen').read_bytes();assert data.count(b'ikip')==0
 expected_field=0
 overlay(a.assets,run.directory/'assets',{})
 runtime=runtime_evidence(a.exe,a.runtime_dir,cwd=run.directory)
 snapshot=lambda:{f.name:digest(f) for f in sorted((sessiondir/'campaign').glob('*.sav'))} if (sessiondir/'campaign').exists() else {}
 before=snapshot();assert len(before)==(0 if a.phase=='save' else 1)
 adoption=dict(diagnostic=a.timeout!=60,acceptance_eligible=a.timeout==60,wall_timeout_seconds=a.timeout,phase=a.phase,root_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),root_dirty=subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip(),root_worktree=str(ROOT),exe=str(a.exe.resolve()),exe_sha256=digest(a.exe),bootstrap_sha256=digest(run.bootstrap),expected_initial_field=expected_field,expected_owned_field=20,manual_start=(a.phase=='save'),initial_approach_frame_limit=180,initial_withdrawal_frame_limit=180,phase_budget_contract='separate approach180 plus withdrawal180; process60s unchanged',starting_baseline="0field20stock, then ordinary UI withdrawal to20live; no appended generators",geometry='unaltered P1 practice campaign terrain',fixture_generator_sha256=digest(run.directory/'assets/dataDir/stages/practice/1.gen'),default_generator_sha256=digest(run.directory/'assets/dataDir/stages/practice/default.gen'),fixture_schedule='identical original generators everyphase; actual production stock withdrawal supplies20live',saved_card_bytes_injected=False,day_or_population_state_injected=False,second_captain_binding='generated manifest p2_second_captain=True and CAPTAINS 2 bootstrap; native randomizer ignores ambient opt-in',before_cards=before)
 adoption['prepared_card_receipt_sha256']=digest(a.prepared_card) if a.prepared_card else None
 adoption['runtime_directory']=str(runtime_dir) if runtime_dir else None
 adoption['runtime']=runtime
 if is_windows():adoption['runtime_dlls_sha256']=runtime_hashes
 info=a.exe.resolve().parent/'BUILD_INFO.txt'
 if info.exists():adoption['CI_build_info']=dict(path=str(info),sha256=digest(info),text=info.read_text(encoding='utf-8'))
 (run.directory/'adoption-inputs.json').write_text(json.dumps(adoption,indent=2),encoding='utf-8')
 (sessiondir/(a.phase+'-run.json')).write_text(json.dumps(dict(directory=str(run.directory)),indent=2),encoding='utf-8')
 print(run.directory,flush=True)
 if a.prepare_only:return
 # The pinned shared launcher performs platform admission before spawning.
 (run.directory/'test-environment.json').write_text(json.dumps(dict(removed=removed,effective={k:v for k,v in os.environ.items() if k.startswith(('PIKMIN_','P2_','SDL_JOYSTICK'))}),indent=2))
 if a.prepared_card and blank_inventory(canonical,sessiondir)!=prepared['inventory']:raise ValueError('Prepared native card changed during SAVE staging')
 done=threading.Event();errors=[]
 def keepalive():
  try:
   while not done.wait(.1):run.poll();run.write_state(True)
  except Exception as e:errors.append(repr(e))
 thread=threading.Thread(target=keepalive);thread.start()
 args=['--randomizer-seed',str(run.bootstrap)];marker='PASS P2_CAPTAIN_ONION_OWNER_SAVE' if a.phase=='save' else 'PASS P2_CAPTAIN_ONION_OWNER_RESUME'
 if a.phase!='save':args.append('--resume-phase')
 if a.negative:args.append({'active':'--force-captain-down','inactive':'--force-inactive-down','null-state':'--force-null-state','missing-manager':'--force-missing-manager'}[a.negative])
 try:result=guarded.launch(a.exe,run.directory,args,[marker],a.timeout,toolchain=runtime_dir,canonical_root=canonical,session_root=sessiondir)
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
 if a.phase!='save':assert 'P2_ONION_MANUAL_START' not in log and 'P2_ONION_INITIAL_UI_WITHDRAW' not in log and 'P2_ONION_STARTUP_ACQUIRE' not in log and 'P2_ONION_INITIAL_HISTORY' not in log and 'P2_ONION_APPROACH_BOUNDARY' not in log,'resume must not execute fresh setup'
 if a.phase=='save':
  assert log.count('[Pikmin Randomizer] START_ONION_HELD stage=0 color=1 stored=20')==1,'actual production stock-held start required'
  assert len(re.findall(r'^P2_ONION_MANUAL_START live=0 stored=20 owner0=0 owner1=0 plate0=0 plate1=0 ordinary_UI_next=1\r?$',log,re.MULTILINE))==1,'one actual initial stock boundary'
  approach=re.findall(r'^P2_ONION_APPROACH_BOUNDARY frames=([1-9][0-9]*) limit=180 selected=0 live=0 stored=20 history_bodies=0 history_events=0 neutral=1 eligible=1 distance=([0-9]+\.[0-9]+) radius=([0-9]+\.[0-9]+) centre=-?[0-9]+\.[0-9]+,-?[0-9]+\.[0-9]+,-?[0-9]+\.[0-9]+\r?$',log,re.MULTILINE)
  assert len(approach)==1 and len(re.findall(r'^P2_ONION_APPROACH_BOUNDARY\b',log,re.MULTILINE))==1,'one explicit approach boundary'
  approach_frames,distance,radius=approach[0]
  assert int(approach_frames)<=180 and 0<float(radius) and float(distance)<=float(radius)+0.001,'bounded natural interaction eligibility'
  assert 0<=log.find('P2_ONION_MANUAL_START')<log.find('P2_ONION_APPROACH_BOUNDARY')<log.find('P2_ONION_INITIAL_UI_WITHDRAW'),'phase order'
  initial=re.findall(r'^P2_ONION_INITIAL_UI_WITHDRAW frames=([1-9][0-9]*) unique=20 live=20 stored=0 owner0=20 owner1=0 plate0=20 plate1=0 input_player=1 whistle=0\r?$',log,re.MULTILINE)
  assert len(initial)==1 and int(initial[0])<=180 and len(re.findall(r'^P2_ONION_INITIAL_UI_WITHDRAW\b',log,re.MULTILINE))==1,'bounded ordinary initial20 UI withdrawal'
  history=re.findall(r'^P2_ONION_INITIAL_HISTORY bodies=20 exit_entries=20 formed=20 unexpected=0 events=([1-9][0-9]*) continuous=1\r?$',log,re.MULTILINE)
  assert len(history)==1 and int(history[0])>=40 and len(re.findall(r'^P2_ONION_INITIAL_HISTORY\b',log,re.MULTILINE))==1,'continuous native initial action history required'
  acquisition=re.findall(r'^P2_ONION_STARTUP_ACQUIRED frames=([1-9][0-9]*) unique=20 live=20 stored=0 owner0=20 owner1=0 plate0=20 plate1=0 acquisition_needed=([01]) observed_B=([01]) observed_Gather=([01]) observed_recruitment=([01]) via_ordinary_SDL=([01])\r?$',log,re.MULTILINE)
  assert len(acquisition)==1 and len(re.findall(r'^P2_ONION_STARTUP_ACQUIRED\b',log,re.MULTILINE))==1,'one complete anchored startup acquisition marker required'
  acquisition_frames,*acquisition_flags=map(int,acquisition[0])
  assert 1<=acquisition_frames<=180 and tuple(acquisition_flags)==(0,0,0,0,0) and acquisition_frames==int(initial[0]),'startup acquisition observation flags must agree'
  worker=re.findall(r'^P2_ONION_WORKER_SETUP needed=(\d+) observed=(\d+) recalls=(\d+) natural=(\d+) original_unique=20\r?$',log,re.MULTILINE)
  assert len(worker)==1 and len(re.findall(r'^P2_ONION_WORKER_SETUP\b',log,re.MULTILINE))==1,'one exact worker summary'
  needed,observed,recalls,natural=map(int,worker[0]);assert needed==observed==recalls==natural==0
  begun=re.findall(r'^P2_ONION_WORKER_EPISODE episode=(\d+) body_token=(\d+) target_token=(\d+)\r?$',log,re.MULTILINE)
  assert len(begun)==needed and len(re.findall(r'^P2_ONION_WORKER_EPISODE\b',log,re.MULTILINE))==needed
  assert [int(e[0]) for e in begun]==list(range(1,needed+1)),'ordered unique native task episodes'
  starts={int(ep):(int(body),int(target)) for ep,body,target in begun}
  assert all(0<=body<20 and target>0 for body,target in starts.values())
  events=re.findall(r'^P2_ONION_WORKER_RECALL episode=(\d+) body_token=(\d+) target_token=(\d+) held_seconds=([0-9.]+) distance=([0-9.]+) radius=([0-9.]+) instant=([01]) after_mode=(\d+) after_state=(\d+) accepted=1\r?$',log,re.MULTILINE)
  natural_events=re.findall(r'^P2_ONION_WORKER_NATURAL episode=(\d+) body_token=(\d+) target_token=(\d+) reason=([1-4]) result=1 before_visible=1 after_visible=1 before_goal=0 after_goal=0 captain=0 mode=1 joined=1 accepted=1\r?$',log,re.MULTILINE)
  assert len(events)==recalls==len(re.findall(r'^P2_ONION_WORKER_RECALL\b',log,re.MULTILINE))
  assert len(natural_events)==natural==len(re.findall(r'^P2_ONION_WORKER_NATURAL\b',log,re.MULTILINE))
  resolved=[]
  for ep,token,target,held,distance,radius,instant,mode,state in events:
   ep=int(ep);assert starts.get(ep)==(int(token),int(target))
   assert float(held)>=.6 and 0<=float(distance)<float(radius),'worker call-time range/hold proof'
   assert (int(mode)==1 and int(state)==0) if instant=='1' else int(state)==26,'actual native whistle path'
   resolved.append(ep)
  for ep,token,target,reason in natural_events:
   ep=int(ep);assert starts.get(ep)==(int(token),int(target));resolved.append(ep)
  assert len(set(resolved))==len(resolved) and set(resolved)==set(starts),'one exact resolution for each task episode'
  assert session.names[50]=='Population: 10 total Red Pikmin','fixed manifest initial check mapping'
  allowed={session.names[50]}
  assert set(session.data['checked'])==allowed and Counter(session.inventory)==Counter(session.rewards[n] for n in allowed),'fresh loop forbids extra work rewards'
  assert 'P2_ONION_DEPOSIT_BOUNDARY live=0 stored=20 owner0=0 owner1=0 plate0=0 plate1=0 startup_whistle_ended=1' in log,'actual deposit boundary required'
  assert len(after)==1 and 'CAMPAIGN_SAVED generation=1' in log
  assert 'P2_ONION_DIARY input=B observed=1' in log and 'P2_ONION_DIARY input=A observed=2' in log,'actual eligible diary inputs required'
  end=re.search(r'PASS P2_CAPTAIN_ONION_OWNER_SAVE day_before=(\d+) day_after=(\d+)',log);assert end and int(end[2])==int(end[1])+1
  facts=re.search(r'P2_SAVE_SCENE .*?live=(\d+) stored=(\d+)',log);assert facts
  baseline=dict(acceptance=a.timeout==60,save_wall_timeout_seconds=a.timeout,cards=after,day=int(end[2]),total=int(facts[1])+int(facts[2]),checked=sorted(session.data['checked']),inventory=dict(session.inventory))
  (sessiondir/'saved-observation.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
 else:
  assert 'P2_ONION_STARTUP_ACQUIRE' not in log and 'P2_ONION_INITIAL_HISTORY' not in log and 'P2_ONION_APPROACH_BOUNDARY' not in log,'resume must not recruit with setup whistle'
  baseline=json.loads((sessiondir/'saved-observation.json').read_text());assert before==after==baseline['cards'],'committed card mutated on resume'
  facts=re.search(r'P2_SAVE_SCENE phase=resume resumed=1 day=(\d+) live=(\d+) stored=(\d+)',log);assert facts
  assert sorted(session.data['checked'])==baseline['checked'] and dict(session.inventory)==baseline['inventory'],'duplicate or new reward on unchanged replay path'
  assert int(facts[1])==baseline['day'] and int(facts[2])+int(facts[3])==baseline['total'],'day/population did not conserve through actual card load'
 (run.directory/'phase-verified.json').write_text(json.dumps(dict(passed=True,diagnostic=a.timeout!=60,acceptance=a.timeout==60,result=result,before=before,after=after,baseline=baseline),indent=2),encoding='utf-8')
 print(json.dumps(result),flush=True)
if __name__=='__main__':main()
