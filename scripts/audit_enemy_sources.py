"""Audit source facts against supplied retail generators and optional native logs.

Read-only. v10 Teki personality layout follows GenObjectTeki::doRead and
TekiPersonality::read: species byte, pellet kind/color bytes, ID32, five ints.
Only campaign generator filenames are included, not Challenge Mode copies.
"""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.enemies import CAMPAIGN_SOURCES, enemy_type
p=argparse.ArgumentParser(); p.add_argument('assets', type=Path); p.add_argument('--native-logs', type=Path)
a=p.parse_args(); rows={}; wanted={row[1] for row in CAMPAIGN_SOURCES}
for stage, folder in enumerate(('practice','stage1','stage2','stage3','last')):
    for path in (a.assets/'dataDir/stages'/folder).glob('*.gen'):
        if not re.fullmatch(r'(default|init|plants|\d+(?:-\d+)?)\.gen', path.name): continue
        day=int(path.stem.split('-')[0])+1 if path.stem[0].isdigit() else 1
        b=path.read_bytes(); start=0
        while (i:=b.find(b'iket',start))>=0:
            start=i+4
            version=int.from_bytes(b[i+4:i+8],'little')
            assert version==10, (path,i,version)
            species=b[i+8]
            if species not in wanted: continue
            protected=b[i+11:i+15]!=b'enon' or int.from_bytes(b[i+31:i+35],'big',signed=True)!=0
            key=(stage,species,protected); rows[key]=min(day,rows.get(key,day))
actual=tuple((*key,day) for key,day in sorted(rows.items()))
assert actual==CAMPAIGN_SOURCES, (actual,CAMPAIGN_SOURCES)
print('PASS: all',len(actual),'campaign source/protection/schedule records match retail files')
if a.native_logs:
    count=0
    for stage, area in enumerate(('impact','forest','navel','spring','trial')):
        for log in (a.native_logs/area).glob('runs/*/native.log'):
            bootstrap=(log.parent/'bootstrap.txt').read_text()
            mask=int(re.search(r'ENEMIES (\d+)',bootstrap)[1])
            for original,actual,protected in re.findall(r'ENEMY_SPAWN original=(\d+) actual=(\d+) protected=(\d+)',log.read_text(errors='replace')):
                original,actual,protected=int(original),int(actual),bool(int(protected))
                assert actual==enemy_type(original,mask,protected)
                if original in wanted: assert (stage,original,protected) in rows, (stage,original,protected)
                count+=1
    assert count
    print('PASS:',count,'native birth records match source protection and permutation')
