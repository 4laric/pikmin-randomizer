"""Disposable one-body White cargo profile; no runtime actor/physics edits."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from scripts.preview_p2_white_acquisition import prepare as acquisition
from scripts.preview_pikmin2_room import records

def prepare(assets, bundle, output):
    for path in (assets,bundle):
        if not Path(path).is_dir():raise ValueError('Explicit legal input directory required')
    acquisition(Path(assets),Path(bundle)/'white',Path(bundle)/'pod',Path(bundle)/'room',Path(output))
    stage=Path(output)/'assets/dataDir/stages/chal0/default.gen'
    rows=records(stage); rewritten=[];pikmin=0
    for source in rows:
        row=bytearray(source);name=row[16:48].rstrip(b'\0')
        if row[72:76]==b'ikip':
            pikmin+=1; uid=pikmin
        elif name==b'preview red onion':
            uid=23;struct.pack_into('>3f',row,48,-40,0,120)
        elif name==b'preview ship':uid=24
        elif name==b'preview ivory':uid=25
        elif name==b'preview treasure bolt':
            uid=26;struct.pack_into('>3f',row,48,170,0,200)
        else:raise ValueError('Unexpected generator source')
        struct.pack_into('<I',row,8,uid);rewritten.append(bytes(row))
    if pikmin!=20:raise ValueError('Exactly20 original Red records required')
    stage.write_bytes(stage.read_bytes()[:20]+struct.pack('>I',len(rewritten))+b''.join(rewritten))
    # Production preview loads this immutable setup profile before gameplay.
    (Path(output)/'p2-pod.txt').write_bytes(b'P2_POD_1 white_carry_smoke 1 1 1 Kochappy 0\n')
    files=[stage,Path(output)/'p2-pod.txt',Path(output)/'p2-white.txt',Path(output)/'assets/dataDir/courses/pikmin2room/room.mod',Path(output)/'assets/dataDir/courses/pikmin2room/room.ini']
    evidence=dict(engineering_profile=True,cargo=dict(uid=26,xyz=[170,0,200],weight=1,capacity=1,value=1),pod=dict(uid=23,xyz=[-40,0,120]),original_red_uids=list(range(1,21)),ivory_uid=25,geometry='Unmodified inherited capped imported room and prototype routes',hashes={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (Path(output)/'white-carry-inputs.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return Path(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','bundle','output'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();print(prepare(a.assets,a.bundle,a.output))
