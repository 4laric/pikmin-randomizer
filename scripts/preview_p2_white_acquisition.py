"""Stage fresh isolated ordinary White Ivory acquisition using local legal assets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preview_pikmin2_room import generator, overlay, records


def prepare(assets, white, pod, output):
    output.mkdir(parents=True, exist_ok=False)
    data=generator(assets)
    starts=[m.start() for m in re.finditer(b'    0.0v',data)]
    rows=[data[a:(starts[i+1] if i+1<len(starts) else len(data))] for i,a in enumerate(starts)]
    rows=[r for r in rows if r[16:48].rstrip(b'\0')!=b'preview dwarf bulborb']
    # P1 Starting walks from the ship; stage it beside the initial squad.
    for i,r in enumerate(rows):
        if r[16:48].rstrip(b'\0')==b'preview ship':
            row=bytearray(r);struct.pack_into('>6f',row,48,-40,0,0,0,0,0);rows[i]=bytes(row)
    template=next(r for r in records(assets/'dataDir/stages/chal0/default.gen') if r[72:80]==b'ssob\x02\x00\x00\x00')
    # Native Generator::readID preserves four-byte IDs by swapping readInt;
    # the Windows integer identity therefore uses little-endian record bytes.
    flower=bytearray(template);struct.pack_into('<I',flower,8,25);flower[16:48]=b'preview ivory'.ljust(32,b'\0')
    struct.pack_into('>6f',flower,48,-25,0,67,0,0,0);struct.pack_into('>I',flower,80,5|(1<<6));rows.append(bytes(flower))
    data=data[:20]+struct.pack('>I',len(rows))+b''.join(rows)
    empty=b'1.0v'+struct.pack('>4fI',-85,0,0,45,0)
    overrides={'dataDir/stages/chal0/default.gen':data}
    for file in (assets/'dataDir/stages/chal0').glob('*.gen'):overrides.setdefault('dataDir/stages/chal0/'+file.name,empty)
    for file in white.glob('*.mod'):overrides['dataDir/courses/pikmin2room/'+file.name]=file.read_bytes()
    for name in ('pod.mod','treasure.mod'):overrides['dataDir/courses/pikmin2room/'+name]=(pod/name).read_bytes()
    overlay(assets,output/'assets',overrides)
    (output/'p2-white.txt').write_bytes((white/'p2-white.txt').read_bytes())
    (output/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    state={'method':'scripted native controller acquisition, no identity/capture/callback injection','initial_pikmin':20,'ivory_uid':25,
           'arena':'P1 practice map, no enemy generator','sources':{'white':str(white),'pod':str(pod),'assets':str(assets)},
           'hashes':{str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [output/'p2-white.txt',output/'p2-pod.txt',output/'assets/dataDir/stages/chal0/default.gen']}}
    (output/'staging.json').write_text(json.dumps(state,indent=2))
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path,required=True);p.add_argument('--white',type=Path,required=True)
    p.add_argument('--pod',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(prepare(a.assets,a.white,a.pod,a.output))
