"""Issue930 bounded ordinary SDL route + actual native boundary/reload on Linux.
Run under a private Xvfb display; source/engine fixture must be built separately.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import create,fingerprint,ITEMS
from scripts.stage_pikmin2_playable_cave import stage
from scripts.play_pikmin2_cave import checkpoint,receipts,stop_owned_child
from experimental.pikmin2_cave_items import parse_items_text
from scripts.pikmin2_cave_linux_runtime import X11Input,matching_modal,validate_end

PREFIX='P2_CAVE_NATIVE_DIALOG '

def require(value,message):
    if not value:raise ValueError(message)

def validate_boundary(state,manifest,placement):
    require(Counter(s for s,m in state['squad'])==Counter({1:18,0:1,2:1}),'actual boundary mixed stock mismatch')
    require(receipts(state['receipts'],placement)==[ITEMS['treasure_water']],'actual once-only water receipt mismatch')
    words=state['buds'].split();expected=manifest['table']['buds']
    used={words[5+2*i]:int(words[6+2*i]) for i in range(len(expected))}
    require(used=={b['slot_id']:2 if b['species']=='blue' else 1 for b in expected},'actual boundary bud budgets mismatch')


def modal_descendant(pid,child):
    for _ in range(8):
        if pid==child:return True
        try:pid=int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[1])
        except (FileNotFoundError,ProcessLookupError):return False
        if pid<=1:return False
    return False


def launch(run,scenario,receipt_path,token):
    env=dict(os.environ)
    for key in list(env):
        if key.startswith(('PIKMIN_CAVE_','PIKMIN_P2_','P2_CAVE_','LD_')):del env[key]
    env.update(P2_CAVE_TEST_SCENARIO=scenario,PIKMIN_P2_ROOM_WINDOW='960x540',
               PIKMIN_P2_ITEM_RECEIPT_PATH=str(receipt_path),SDL_AUDIODRIVER='dummy',
               SDL_VIDEODRIVER='x11',PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',PIKMIN_RANDOMIZER_TEST_HEADLESS='0')
    (run/'pikmin_settings.conf').write_text('debugKeys=0\nwindowWidth=960\nwindowHeight=540\ndisplayMode=0\n')
    backend=X11Input();baseline={w['window'] for w in backend.windows()}
    child=None;modal_fd=None;events=[];begin=None;end=None;pressed=False;ready=False;error=None;raw=[]
    deadline=time.monotonic()+60
    try:
        child=subprocess.Popen([str(run/'nectar.exe'),'--experimental-pikmin2-room'],cwd=run,env=env,
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        os.set_blocking(child.stdout.fileno(),False);selector=selectors.DefaultSelector();selector.register(child.stdout,selectors.EVENT_READ)
        pending=b''
        while True:
            require(time.monotonic()<deadline,'60-second owned-child deadline exceeded')
            for key,mask in selector.select(.02):
                data=os.read(child.stdout.fileno(),65536)
                if data:pending+=data
                while b'\n' in pending:
                    line,pending=pending.split(b'\n',1);text=line.decode(errors='replace');raw.append(text)
                    if 'P2_CAVE_MIXED_BOUNDARY_READY' in text:ready=True
                    if text.startswith(PREFIX):
                        record=json.loads(text[len(PREFIX):]);events.append(record)
                        if record.get('event')=='begin':
                            require(ready and begin is None and record.get('pid')==child.pid,'uncorrelated native dialog')
                            require((record.get('phase'),record.get('action'),record.get('title'),record.get('cave'),record.get('floor'),record.get('token'))==('floor','descend','Emergence Cave','forest_1',1,token),'foreign native boundary dialog')
                            require(record.get('buttons')==[{'id':0,'text':'Stay','flags':2,'return_default':False,'escape_default':True},{'id':1,'text':'Descend','flags':1,'return_default':True,'escape_default':False}],'native dialog buttons changed')
                            begin=record
                        elif record.get('event')=='end':
                            require(begin is not None,'dialog ended without begin');validate_end(record,begin,pressed);end=record
            if begin and not pressed:
                modal=matching_modal(backend.windows(),begin,baseline)
                if modal:
                    owner=modal['owner_pid'];require(modal_descendant(owner,child.pid),'native modal not owned by this child')
                    modal_fd=os.pidfd_open(owner);backend.press_return(modal['window']);pressed=True
                    events.append({'event':'actual-X11-Return','window':modal['window'],'owner_pid':owner})
            if child.poll() is not None:
                # Drain any remaining kernel pipe bytes before evaluating markers.
                data=child.stdout.read()
                if data:pending+=data
                if pending:raw.extend(pending.decode(errors='replace').splitlines())
                break
        if scenario=='route':require(child.returncode==42 and begin and end and pressed,'actual confirmed boundary exit42 missing')
        else:require(child.returncode==0 and any('PASS CAVE_MIXED_ROUTE_RESTORE' in line for line in raw),'actual native reload failed')
    except BaseException as exc:
        error=repr(exc);raise
    finally:
        if child is not None:stop_owned_child(child)
        if modal_fd is not None:
            try:signal.pidfd_send_signal(modal_fd,signal.SIGTERM)
            except ProcessLookupError:pass
            os.close(modal_fd)
        backend.close()
        (run/'native.log').write_text('\n'.join(raw)+'\n')
        (run/'supervisor.json').write_text(json.dumps({'scenario':scenario,'exit_code':child.returncode if child else None,'error':error,'dialog_events':events,'elapsed_seconds':60-(deadline-time.monotonic())},indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','pod','fixture','generator','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();require(os.name!='nt','Linux supervised route entrypoint')
    output=args.output.resolve();require(not output.exists(),'fresh output required');output.mkdir(parents=True)
    manifest=create('930','Player1');token=fingerprint(manifest)[:32]
    receipt_path=output/'receipts.txt';receipt_path.write_text('P2_RECEIPTS_1\n')
    initial=output/'route';stage(manifest,args.assets,args.pod,args.fixture,args.generator,initial)
    placement=parse_items_text((initial/'p2-cave-items.txt').read_text())
    launch(initial,'route',receipt_path,token)
    state=checkpoint((initial/'p2-cave-transfer.txt').read_text(),(initial/'p2-cave-bud-transfer.txt').read_text(),receipt_path.read_text(),manifest,placement)
    validate_boundary(state,manifest,placement)
    (output/'checkpoint.json').write_text(json.dumps(state,indent=2)+'\n')
    before=receipt_path.read_bytes();reload=output/'reload'
    stage(manifest,args.assets,args.pod,args.fixture,args.generator,reload,checkpoint=state)
    launch(reload,'restore',receipt_path,token);require(receipt_path.read_bytes()==before,'reload changed durable receipts')
    (output/'result.json').write_text(json.dumps({'passed':True,'ordinary_SDL_route':True,'production_F6_confirmed':True,'actual_mixed_reload':True,'campaign_SAVE_accepted':False},indent=2)+'\n')

if __name__=='__main__':main()
