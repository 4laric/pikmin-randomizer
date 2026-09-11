"""Compare a bounded offline parser with native disk/cache reads in all five maps."""
import argparse, json, os, re, subprocess, sys, time, _winapi
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_enemy_slots import audit
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
p=argparse.ArgumentParser()
for n in ('exe','assets','output'):p.add_argument('--'+n,type=Path,required=True)
p.add_argument('--per-spawn',action='store_true')
p.add_argument('--groups',action='store_true')
p.add_argument('--respawn',action='store_true')
p.add_argument('--bad-cache',action='store_true',help='Require explicit rejection of a corrupted tagged cache record')
a=p.parse_args();facts=audit(a.assets);evidence={}
for stage,area in enumerate(('impact','forest','navel','spring','trial')):
    m=generate('spawn-audit-'+area,'ap',collection_checks=True,starting_area=area,starting_flarlic=1,per_spawn_enemies=a.per_spawn,group_spawn_enemies=a.groups)
    s=Session(m,a.output.resolve()/area);r=NativeRun(s);r.write_state(True)
    (r.directory/'audit-files.txt').write_text('\n'.join(f['file'] for f in facts['files'] if f['stage']==stage)+'\n')
    _winapi.CreateJunction(str(a.assets.resolve()),str(r.directory/'assets'))
    env=dict(os.environ,PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',SDL_AUDIODRIVER='dummy',PIKMIN_RANDOMIZER_TEST_SCRIPT='spawn-audit');env.pop('BBFT_PORT',None)
    if a.bad_cache:
        assert a.per_spawn
        env['PIKMIN_RANDOMIZER_TEST_BAD_SLOT_CACHE']='1'
    if a.respawn:
        assert a.groups
        env['PIKMIN_RANDOMIZER_TEST_GROUP_RESPAWN']='1'
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    log=r.directory/'native.log'
    with log.open('w',encoding='utf-8') as stream:
        process=subprocess.Popen([str(a.exe.resolve()),'--randomizer-seed',str(r.bootstrap)],cwd=r.directory,env=env,startupinfo=startup,stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+120
            while process.poll() is None and time.monotonic()<deadline:
                r.poll();r.write_state(True);time.sleep(.1)
            assert process.poll()==(2 if a.bad_cache else 0), f'exit {process.poll()}; {log}'
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    text=log.read_text(errors='replace');seen={}
    if a.bad_cache:
        assert 'incompatible enemy slot cache record' in text,log
        print('PASS malformed tagged cache rejected before restore',flush=True)
        sys.exit(0)
    for line in text.splitlines():
        if not line.startswith('SPAWN_AUDIT '):continue
        fields=dict(x.split('=',1) for x in line.split()[1:]);identity=f"{fields['stage']}/{fields['file']}@{fields['offset']}"
        assert identity not in seen;seen[identity]=fields
    expected=[row for row in facts['slots'] if row['stage']==stage]
    assert set(seen)=={row['id'] for row in expected},(stage,len(seen),len(expected),log)
    for row in expected:
        fields=seen[row['id']]
        assert fields['kind']==row['kind'] and int(fields['species'])==row['species'],row['id']
        assert list(map(int,fields['cache'].split(',')))==row['cache_position'],row['id']
        assert int(fields['count'])==row['count_max'] and int(fields['respawn'])==row['respawn_days'],row['id']
        assert int(fields['flags'])==row['carry_flags'],row['id']
        protected=row['kind']=='boss' or row['personality']['pellet_id']!='none' or row['personality']['parameter0']!=0
        assert int(fields['protected'])==protected,row['id']
        evidence[row['id']]={'anchor_terrain':int(fields['terrain']), 'disk_and_cache_roundtrip':True}
    assert 'TEST_ONLY spawn_audit_pass' in text,log
    if a.per_spawn or a.groups:
        assignments={row['uid']:row['actual'] for row in m['spawn_layout']['assignments']}
        if a.groups:assignments.update((r['uid'],r['actual']) for r in m['group_layout']['assignments'])
        adults=[]
        for line in text.splitlines():
            if not line.startswith('ENEMY_SLOT_BIRTH '):continue
            fields=dict(x.split('=',1) for x in line.split()[1:])
            if int(fields['original']) in (4,32):
                assert assignments[int(fields['uid'])]==int(fields['actual']),line
                adults.append(int(fields['actual']))
            elif int(fields['uid']) in assignments:assert assignments[int(fields['uid'])]==int(fields['actual']),line
            else:assert fields['actual']==fields['original'],line
        if stage in (1,3):assert set(adults)=={4,32},(stage,adults,log)
        cached={}
        for line in text.splitlines():
            if line.startswith('CACHE_SLOT '):
                fields=dict(x.split('=',1) for x in line.split()[1:])
                cached[int(fields['uid'])]=int(fields['actual'])
        from randomizer.spawn_data import ADULT_SLOTS, GROUP_SLOTS
        rows=ADULT_SLOTS+(GROUP_SLOTS if a.groups else ())
        assert cached=={row['uid']:assignments[row['uid']] for row in rows if row['stage']==stage},(stage,cached)
        if a.groups:
            survivors={}
            for line in text.splitlines():
                if line.startswith('GROUP_SURVIVORS '):
                    fields=dict(x.split('=',1) for x in line.split()[1:]);survivors[int(fields['uid'])]=int(fields['count'])
            assert survivors=={row['uid']:row['count']-(0 if a.respawn else 1) for row in GROUP_SLOTS if row['stage']==stage},(stage,survivors)
        assert 'TEST_ONLY spawn_cache_pass' in text
    print('PASS',area,len(seen),'disk/cache records',flush=True)
(a.output/'evidence.json').write_text(json.dumps({'catalog':facts['sha256'],'slots':evidence},indent=2)+'\n')
