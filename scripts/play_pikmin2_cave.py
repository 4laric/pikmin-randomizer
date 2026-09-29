"""Launch the isolated bounded cave; F6 at the far hole saves a re-entry checkpoint.

This package does not run the AP network client or apply campaign item effects.
Its seed checks are journaled through Session for later use with the same seed.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.seed import validate,fingerprint
from randomizer.session import Session,atomic_write
from randomizer.cave_floor import ITEMS
from experimental.pikmin2_cave_items import parse_items_text
from scripts.stage_pikmin2_playable_cave import stage


def receipts(text,placement):
    words=text.split()
    if not words or words[0]!='P2_RECEIPTS_1' or (len(words)-1)%4:
        raise ValueError('invalid cave receipt ledger')
    expected={('treasure:forest_1:f1:'+e['slot_id'],e['host']):ITEMS[e['item']] for e in placement['items']}
    seen=set(); names=[]
    for i in range(1,len(words),4):
        seed,reward,host,event=words[i:i+4]
        if seed!=str(placement['seed']) or event!='cave_treasure' or (reward,host) not in expected or reward in seen:
            raise ValueError('foreign, unknown or duplicate cave receipt')
        seen.add(reward); names.append(expected[reward,host])
    return names


def checkpoint(transfer,buds,receipt_text,manifest,placement):
    words=transfer.split()
    if len(words)<5 or words[:2]!=['P2_CAVE_TRANSFER_1',fingerprint(manifest)[:32]] or words[2]!='1':
        raise ValueError('foreign cave transfer')
    health=float(words[3]); count=int(words[4])
    if not math.isfinite(health) or not 0<health<=1 or not 1<=count<=100 or len(words)!=5+2*count:
        raise ValueError('cave failed or invalid squad; refusing fresh starter reset')
    squad=[[int(words[5+i*2]),int(words[6+i*2])] for i in range(count)]
    if any(s not in (0,1,2) or m not in (0,1,2) for s,m in squad): raise ValueError('unsupported squad')
    w=buds.split(); table=manifest['p2_cave_floor']['table']
    expected=['P2_CAVE_BUD_STATE_1',str(placement['seed']),'forest_1','1',str(len(table['buds']))]
    if w[:5]!=expected or len(w)!=5+2*len(table['buds']): raise ValueError('foreign bud checkpoint')
    for i,b in enumerate(table['buds']):
        if w[5+2*i]!=b['slot_id'] or not 0<=int(w[6+2*i])<=b['count']: raise ValueError('invalid bud budget')
    receipts(receipt_text,placement)
    return dict(schema=1,fingerprint=fingerprint(manifest),health=health,squad=squad,buds=buds,receipts=receipt_text)


def recover_pending(session_dir,manifest,placement,receipt_text,live_paths=()):
    pending=session_dir/'pending.json'
    if not pending.exists(): return
    record=json.loads(pending.read_text())
    run=Path(record['run']).resolve()
    if record.get('fingerprint')!=fingerprint(manifest) or run.parent!=(session_dir/'runs').resolve():
        raise ValueError('foreign pending run')
    if (run/'nectar.exe').resolve() in {Path(p).resolve() for p in live_paths}:
        raise RuntimeError('This cave process is still running; refusing a concurrent launch.')
    transfer=run/'p2-cave-transfer.txt'
    if transfer.exists():
        state=checkpoint(transfer.read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),receipt_text,manifest,placement)
        atomic_write(session_dir/'checkpoint.json',json.dumps(state,indent=2)+'\n')


def runtime_capacity():
    # Preserve other owners' runtimes. Read-only Windows process count; no kill.
    running=subprocess.run(['powershell','-NoProfile','-Command',
        "$caveOs=Get-CimInstance Win32_OperatingSystem; ConvertTo-Json @{paths=@(Get-Process nectar -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path); freeKiB=$caveOs.FreePhysicalMemory; totalKiB=$caveOs.TotalVisibleMemorySize}"],
        capture_output=True,text=True,check=True)
    capacity=json.loads(running.stdout)
    live_paths=capacity['paths']
    if len(live_paths)>=6: raise RuntimeError('Six nectar processes already run; wait for runtime capacity.')
    # Conservative operating guard, not a demonstrated machine safety threshold.
    if capacity['freeKiB'] < max(4*1024*1024,capacity['totalKiB']*.15):
        raise RuntimeError('Insufficient free memory for another private runtime.')
    return live_paths


def main(package):
    package=Path(package).resolve()
    meta=json.loads((package/'package.json').read_text())
    for name,digest in meta['files'].items():
        if Path(name).name!=name or hashlib.sha256((package/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('package input changed: '+name)
    manifest=json.loads((package/'seed.json').read_text()); validate(manifest)
    if fingerprint(manifest)!=meta['fingerprint']: raise ValueError('foreign package seed')
    live_paths=runtime_capacity()
    session_dir=package/'session'; session_dir.mkdir(exist_ok=True)
    # OS lock is automatically released after a supervisor crash; no stale lock deletion.
    import msvcrt
    with (session_dir/'launch.lock').open('a+b') as lock:
        lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        session=Session(manifest,session_dir/'checks')
        placement=parse_items_text((package/'p2-cave-items.txt').read_text())
        receipt_path=session_dir/'receipts.txt'
        if not receipt_path.exists(): atomic_write(receipt_path,'P2_RECEIPTS_1\n')
        for name in receipts(receipt_path.read_text(),placement): session.collect(name)
        recover_pending(session_dir,manifest,placement,receipt_path.read_text(),live_paths)
        saved=session_dir/'checkpoint.json'
        prior=json.loads(saved.read_text()) if saved.exists() else None
        if prior:
            # Reparse serialized values against the current contract, not only the digest.
            transfer='P2_CAVE_TRANSFER_1\n'+fingerprint(manifest)[:32]+'\n1 '+str(prior['health'])+' '+str(len(prior['squad']))+'\n'+''.join(f'{s} {m}\n' for s,m in prior['squad'])
            if prior.get('fingerprint')!=fingerprint(manifest): raise ValueError('foreign saved checkpoint')
            checkpoint(transfer,prior['buds'],prior['receipts'],manifest,placement)
        run=session_dir/'runs'/uuid.uuid4().hex
        stage(manifest,Path(meta['assets']),Path(meta['pod']),package/'nectar.exe',package/'cave-generator.exe',run,meta['salt'],prior)
        atomic_write(session_dir/'pending.json',json.dumps({'run':str(run),'fingerprint':fingerprint(manifest)}))
        env=os.environ.copy()
        for key in list(env):
            if key.startswith('PIKMIN_CAVE_') or key.startswith('PIKMIN_P2_'):
                del env[key]
        env['PIKMIN_P2_ROOM_WINDOW']='960x540'
        env['PIKMIN_P2_ITEM_RECEIPT_PATH']=str(receipt_path)
        env['PATH']='C:\\msys64\\mingw64\\bin;'+env.get('PATH','')
        with (run/'native.log').open('w') as log:
            # Shared across packages/checkouts, held only through process creation.
            # Other runtime families must still coordinate admission with this lane.
            admission=Path(tempfile.gettempdir())/'pikmin-randomizer-runtime-admission.lock'
            with admission.open('a+b') as gate:
                gate.seek(0); gate.write(b'0'); gate.flush(); gate.seek(0)
                msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
                runtime_capacity()
                child=subprocess.Popen([str(run/'nectar.exe'),'--experimental-pikmin2-room'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT)
            returncode=child.wait()
        # Receipts survive even an unsaved crash; a repeated process cannot regrant.
        current=receipt_path.read_text()
        for name in receipts(current,placement): session.collect(name)
        if returncode==42:
            state=checkpoint((run/'p2-cave-transfer.txt').read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),current,manifest,placement)
            atomic_write(saved,json.dumps(state,indent=2)+'\n')
            print('Checkpoint saved. Relaunch to re-enter this bounded floor with the saved squad and collected treasure removed.')
        elif returncode: raise RuntimeError('native exited '+str(returncode)+'; see '+str(run/'native.log'))
        else: print('Unsaved exit: next launch uses the last floor-boundary squad; durable treasure checks remain collected.')


if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: play_pikmin2_cave.py PACKAGE')
    main(sys.argv[1])
