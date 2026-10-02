"""Direct five-phase White campaign smoke; owned user units, actual gameplay oracles."""
import argparse,json,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_p2_white_campaign import phase_limit,prepare_session,prepare_resume,verify_native_card,assess_positive,assess_resume,rows,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--stage',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--root-pin',required=True);p.add_argument('--native-pin',required=True)
 p.add_argument('--source-sha',required=True);p.add_argument('--exe-sha',required=True);a=p.parse_args()
 if digest(a.exe)!=a.exe_sha:raise ValueError('Executable differs from collected build')
 a.out.mkdir(parents=True,exist_ok=False);results=[];positive_session=None;positive=None;card=None
 try:
  for mode in ('ready','forced-down','paused-down','positive','resume'):
   if digest(a.exe)!=a.exe_sha:raise ValueError('Executable changed before phase')
   if mode=='resume':
    session=positive_session;prepared=prepare_resume(a.stage,session,expected_day=positive['day'],expected_p1_stock=positive['p1_stock'],generation=positive['generation'])
   else:
    session=a.out/mode;prepared=prepare_session(a.stage,session)
    if mode=='positive':positive_session=session
   directory=session/('white1191-phase29-'+mode+'-'+uuid.uuid4().hex);directory.mkdir()
   request={'exe':str(a.exe.resolve()),'stage':str(a.stage.resolve()),'session_directory':str(session.resolve()),
            'run_directory':str(directory.resolve()),'mode':mode,'root_pin':a.root_pin,'native_pin':a.native_pin,
            'source_sha':a.source_sha,'bootstrap':prepared['bootstrap'],'expected_day':positive['day'] if mode=='resume' else None,
            'expected_p1_stock':positive['p1_stock'] if mode=='resume' else None,'saved_generation':positive['generation'] if mode=='resume' else None}
   request_path=directory/'request.json';request_path.write_text(json.dumps(request,indent=2)+'\n')
   wrapper=Path(__file__).resolve().parent/'run_p2_white_campaign_phase.py'
   with (directory/'supervisor.log').open('xb') as log:
    process=subprocess.Popen([sys.executable,'-I','-B',str(wrapper),'--request',str(request_path)],cwd=directory,stdout=log,stderr=subprocess.STDOUT)
    try:code=process.wait(timeout=phase_limit(mode))
    except subprocess.TimeoutExpired:
     process.kill();process.wait(timeout=1);raise ValueError('Frontend selected whole deadline; owned user unit independent kill policy remains active')
   outer=json.loads((directory/'phase-result.json').read_text());results.append({'mode':mode,'directory':str(directory),'supervisor_exit':code,'result':outer})
   if code or outer['error'] or outer['cleanup_errors'] or not outer['containment_retirement']:raise ValueError('Phase failed: '+mode)
   inner=outer['worker']['result'];text=(directory/'native.log').read_text()
   if mode=='ready':
    if 'P2_WHITE_CAMPAIGN_READY_PASS' not in text or 'P2_WHITE_CAMPAIGN_WINDOW width=960 height=540 centered=1' not in text:raise ValueError('Actual ready/window marker missing')
   elif mode in ('forced-down','paused-down'):
    if 'P2_FIXTURE_CAPTAIN_DOWN' not in text or 'P2_WHITE_CAMPAIGN_READY_PASS' in text:raise ValueError('Actual guard negative missing or falsely passed')
   elif mode=='positive':
    saves=rows(text,'P2_WHITE_CAMPAIGN_SAVE_PASS');stocks=rows(text,'P2_WHITE_CAMPAIGN_P1_SAVE_STOCK')
    if len(saves)!=1 or len(stocks)!=1:raise ValueError('Actual unique native SAVE and P1 stock required')
    keys=['b_leaf','b_bud','b_flower','r_leaf','r_bud','r_flower','y_leaf','y_bud','y_flower']
    saved_stock=[int(stocks[0][key]) for key in keys];generation=int(saves[0]['generation']);day=int(saves[0]['day'])
    manifest=json.loads((session/'manifest.json').read_text())
    card=verify_native_card(session/'campaign'/f'{generation:020d}.sav',fingerprint=prepared['manifest_fingerprint'],generation=generation,
                           stage=a.stage,check_count=len(manifest['locations']),expected_day=day,expected_p1_stock=saved_stock)
    positive=assess_positive(text,exit_code=inner['exit_code'],elapsed=inner['elapsed'],timed_out=inner['timed_out'],source_proof=True,card_proof=card,phase_budget=phase_limit(mode))
    positive['day']=day;results[-1]['mechanic_assessment']=positive;results[-1]['card']=card
   else:
    fresh=verify_native_card(session/'campaign'/f"{positive['generation']:020d}.sav",fingerprint=prepared['manifest_fingerprint'],generation=positive['generation'],
                             stage=a.stage,check_count=len(json.loads((session/'manifest.json').read_text())['locations']),expected_day=positive['day'],expected_p1_stock=positive['p1_stock'])
    results[-1]['mechanic_assessment']=assess_resume(text,exit_code=inner['exit_code'],elapsed=inner['elapsed'],timed_out=inner['timed_out'],saved_card=card,current_card=fresh,source_proof=True,expected_day=positive['day'])
  status={'passed':True,'phases':results,'human_playtested':False,'full_campaign_accepted':False}
 except Exception as exc:
  status={'passed':False,'error':str(exc),'phases':results,'human_playtested':False,'full_campaign_accepted':False}
 (a.out/'campaign-result.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status));return 0 if status['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
