"""Native campaign mapping, strict bootstrap rejection and session recovery."""
import subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
for case in ('valid','species','uid','count','catalog','version'):
    with tempfile.TemporaryDirectory() as directory:
        m=generate('campaign-probe','ap',campaign_enemies=True)
        s=Session(m,directory);r=NativeRun(s);r.write_state(True)
        text=r.bootstrap.read_text();line=next(l for l in text.splitlines() if l.startswith('ENEMY_CAMPAIGN '));fields=line.split()
        if case=='species':fields[6]='22'
        if case=='uid':fields[5]='0'
        if case=='count':fields[3]='71'
        if case=='catalog':fields[2]='0'*64
        if case=='version':fields[1]='2'
        r.bootstrap.write_text(text.replace(line,' '.join(fields)))
        result=subprocess.run([str(Path(sys.argv[1]).resolve()),'--randomizer-seed',str(r.bootstrap),'--campaign-probe'],capture_output=True,text=True,timeout=15)
        if case=='valid':
            assert result.returncode==0,result.stderr
            actual={int(l.split()[1]):int(l.split()[2]) for l in result.stdout.splitlines() if l.startswith('CAMPAIGN_PROBE ')}
            assert actual=={a['uid']:a['actual'] for a in m['campaign_layout']['assignments']}
            r.poll();assert r.handshaken
            (r.directory/'checks.txt').write_text('0\n')
            assert Session(m,directory).data['checked']==[s.names[0]]
        else:assert result.returncode!=0,case
print('PASS 72 native assignments, protected registry, handshake/journal recovery and five malformed campaign bootstraps')
