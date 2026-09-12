"""Build a private asset overlay for the post-v0.1 P2 room experiment."""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import uuid


def records(path):
    data=path.read_bytes()
    if data[:4] != b'1.0v': raise ValueError('Expected v0.1 generator fixture source')
    starts=[m.start() for m in re.finditer(b'    0.0v',data)]
    if not starts or starts[0]!=24 or len(starts)!=struct.unpack_from('>I',data,20)[0]:
        raise ValueError('Unsupported template record framing')
    return [data[s:(starts[i+1] if i+1<len(starts) else len(data))] for i,s in enumerate(starts)]


def generator(assets):
    base=assets/'dataDir/stages'
    challenge=records(base/'chal0/default.gen')
    practice=records(base/'practice/default.gen')
    if challenge[5][72:76]!=b'ikip' or challenge[9][72:76]!=b'iket': raise ValueError('Unexpected templates')
    if practice[1][16:24]!=b'red goal' or practice[3][16:24]!=b'ufo goal': raise ValueError('Unexpected goal templates')
    entries=[]
    def add(record,xyz,name):
        r=bytearray(record);r[8:12]=struct.pack('>I',len(entries)+1)
        r[16:48]=name.encode('ascii').ljust(32,b'\0')
        r[48:72]=struct.pack('>6f',*xyz,0,0,0)
        entries.append(bytes(r))
    add(practice[1],(-220,0,-180),'preview red onion')
    add(practice[3],(170,0,170),'preview ship')
    piki=bytearray(challenge[5])
    if piki[80:84]!=b'p00\x04' or piki[88:92]!=b'p01\x04': raise ValueError('Unexpected Piki fields')
    struct.pack_into('>I',piki,84,2)  # formation, not buried sprout
    struct.pack_into('>I',piki,92,1)  # native Red
    type_start=piki.index(b'nota0.0v',96)
    count_start=piki.index(b'p00\x04',type_start)+4
    struct.pack_into('>I',piki,count_start,1)  # one Piki per selected placement
    for i in range(20): add(piki,(-110+(i%5)*12,0,-20+(i//5)*12),'preview red pikmin')
    dwarf=bytearray(challenge[9]);dwarf[80]=3  # TEKI_Chappy (native Dwarf Bulborb), generator v10 byte enum
    # The source posy generator is an at-once pair; retain its framing but spawn one actor.
    type_start=dwarf.index(b'nota0.0v',80)
    count_start=dwarf.index(b'p00\x04',type_start)+4
    if struct.unpack_from('>I',dwarf,count_start)[0]!=2: raise ValueError('Unexpected source enemy count')
    struct.pack_into('>I',dwarf,count_start,1)
    add(dwarf,(185,0,-180),'preview dwarf bulborb')
    treasure=bytearray(challenge[6]);treasure[80:84]=b'50rp'
    add(treasure,(-175,0,-100),'preview treasure bolt')
    return b'1.0v'+struct.pack('>4fI',-85,0,0,45,len(entries))+b''.join(entries)


def overlay(source,dest,overrides):
    """Only ancestor directories of replacements are writable; shared files never edited."""
    import _winapi
    dest.mkdir(parents=True,exist_ok=False)
    names={p.name for p in source.iterdir()}|{k.split('/')[0] for k in overrides}
    for name in sorted(names):
        src=source/name;dst=dest/name
        if name in overrides:
            dst.write_bytes(overrides[name]);continue
        children={k[len(name)+1:]:v for k,v in overrides.items() if k.startswith(name+'/')}
        if children:
            if src.is_dir():overlay(src,dst,children)
            else:
                dst.mkdir()
                for k,v in children.items():
                    f=dst/k;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(v)
        elif src.is_dir():_winapi.CreateJunction(str(src),str(dst))
        else:os.link(src,dst)


def prepare(assets,converted,output):
    run=output.resolve()/uuid.uuid4().hex
    run.mkdir(parents=True)
    stage=(assets/'dataDir/stages/chal0.ini').read_bytes()
    stage=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/pikmin2room/room.mod',stage)
    stage=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -85.0 0.0',stage)
    empty=b'1.0v'+struct.pack('>4fI',-85,0,0,45,0)
    overrides={'dataDir/stages/chal0.ini':stage,'dataDir/stages/chal0/default.gen':generator(assets),
      'dataDir/stages/chal0/plants.gen':empty,
      'dataDir/courses/pikmin2room/room.mod':(converted/'room.mod').read_bytes(),
      'dataDir/courses/pikmin2room/room.ini':(converted/'room.ini').read_bytes()}
    overrides['dataDir/courses/pikmin2room/treasure.mod']=(converted/'treasure.mod').read_bytes()
    # Suppress any other generator sources in this private layout directory.
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    overlay(assets,run/'assets',overrides)
    (run/'preview.json').write_text(json.dumps(dict(room='room_4x4a_4_conc',experimental=True,ap=False,save_resume=False),indent=2))
    return run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--converted',type=Path,default=Path('output/pikmin2-room105'))
    p.add_argument('--output',type=Path,default=Path('output/pikmin2-room-preview'))
    p.add_argument('--exe',type=Path)
    a=p.parse_args();run=prepare(a.assets.resolve(),a.converted.resolve(),a.output)
    print(run,flush=True)
    if a.exe:
        with (run/'native.log').open('w',encoding='utf8') as log:
            result=subprocess.run([str(a.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise SystemExit(f'Native exit {result.returncode}: {run / "native.log"}')

if __name__=='__main__':main()
