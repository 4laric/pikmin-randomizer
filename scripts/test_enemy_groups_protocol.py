import subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
for case in ('valid','species','uid','hash','count'):
    with tempfile.TemporaryDirectory() as folder:
        m=generate('group-probe','ap',group_spawn_enemies=True);s=Session(m,folder);r=NativeRun(s);r.write_state(True)
        text=r.bootstrap.read_text();line=next(l for l in text.splitlines() if l.startswith('ENEMY_GROUPS '));fields=line.split()
        if case=='species':fields[4]='4'
        if case=='uid':fields[3]='1'
        if case=='hash':fields[1]='0'*64
        if case=='count':fields[2]='13'
        r.bootstrap.write_text(text.replace(line,' '.join(fields)))
        result=subprocess.run([str(Path(sys.argv[1]).resolve()),'--randomizer-seed',str(r.bootstrap),'--group-probe'],capture_output=True,text=True,timeout=15)
        if case=='valid':
            assert result.returncode==0,result.stderr
            actual={int(l.split()[1]):int(l.split()[2]) for l in result.stdout.splitlines() if l.startswith('GROUP_PROBE ')}
            assert actual=={r['uid']:r['actual'] for r in m['group_layout']['assignments']}
            r.poll();assert r.handshaken
            assert Session(m,folder).data==s.data
        else:assert result.returncode!=0,case
print('PASS group choice/identity/protection/handshake and four invalid bootstraps')
