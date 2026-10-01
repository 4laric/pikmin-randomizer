"""Fresh bounded White refund or full-player-pluck acceptance; local assets only."""
import argparse, hashlib, json, os, sys, uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.preview_p2_white_acquisition import prepare

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('workspace','exe','assets','white','pod','room'): p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--mode',choices=('refund','full','negative','manual','startup-check'),default='refund')
 a=p.parse_args();root=a.workspace.resolve();sys.path.insert(0,str(root/'scripts'))
 from run_pikmin2_fixture import launch
 run=root/'output/white-refund-pluck'/('run-'+a.mode+'-'+uuid.uuid4().hex[:10])
 for k in list(os.environ):
  if k.startswith(('P2_WHITE_','PIKMIN_RANDOMIZER_AUTOPLAY','PIKMIN_P2_')): del os.environ[k]
 os.environ['PIKMIN_RANDOMIZER_AUTOPLAY']='0'
 os.environ['PIKMIN_P2_ROOM_WINDOW']='960x540'
 if a.mode=='refund': os.environ['P2_WHITE_REFUND_SCENARIO']='1'
 if a.mode=='negative': os.environ['P2_WHITE_REFUND_PLUCK_FORCE_CAPTAIN_DOWN']='1'
 if a.mode in ('manual','startup-check'):os.environ['P2_WHITE_MANUAL_SMOKE']='1'
 if a.mode=='startup-check':os.environ['P2_WHITE_MANUAL_STARTUP_CHECK']='1'
 prepare(a.assets,a.white,a.pod,a.room,run)
 disclosure=dict(mode=a.mode,starting='20 Red staged through current overlay',input='actual SDL virtual P1 and native UI polling',movies='skipped',tutorial_flags='suppressed',actor_identity_capture_budget_timer_conversion_pluck_injection=False,timeout_seconds=60,runner_sha256=sha(__file__),exe_sha256=sha(a.exe),human_feedback='unrecorded')
 (run/'disclosure.json').write_text(json.dumps(disclosure,indent=2))
 marker={'refund':'P2_WHITE_REFUND_PASS','full':'P2_WHITE_FULL_PLUCK_PASS','negative':'P2_FIXTURE_CAPTAIN_DOWN','manual':'P2_WHITE_MANUAL_SMOKE_READY','startup-check':'P2_WHITE_MANUAL_SMOKE_READY'}[a.mode]
 result=launch(a.exe,run,['--experimental-pikmin2-room'],[marker],60)
 log=(run/'native.log').read_text(errors='replace')
 expected=86 if a.mode=='negative' else 0
 checks=dict(exit=result.get('exit_code')==expected,bounded=not result.get('timed_out') and result.get('timeout_seconds')==60,marker=marker in log)
 if a.mode=='negative':checks['no_success']='P2_WHITE_REFUND_PASS' not in log and 'P2_WHITE_FULL_PLUCK_PASS' not in log
 elif a.mode in ('refund','full'):checks['captain_safe']=not result.get('captain_down')
 report=dict(mode=a.mode,passed=all(checks.values()),checks=checks,raw_result=result,full_campaign_accepted=False,outputs={f.name:sha(f) for f in run.iterdir() if f.is_file()})
 (run/'assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(run=str(run),assessment=report),indent=2))
 if a.mode=='manual' and result.get('exit_code')==77: return 77
 return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
