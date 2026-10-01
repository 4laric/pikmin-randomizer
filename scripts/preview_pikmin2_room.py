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


def generator(assets, reds=20):
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
    # Shared room-preview squad: default 20 reds. A family arena that needs more
    # (e.g. lane 27 BombSarai, whose carrier's area bombs otherwise wipe a 20-red
    # squad before it can be killed) passes reds= explicitly to its staging call.
    if reds < 0 or reds > 100: raise ValueError('reds out of range')
    for i in range(reds): add(piki,(-110+(i%5)*12,0,-20+(i//5)*12),'preview red pikmin')
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


def _pikmin_template(assets):
    blob=generator(assets)
    starts=[i for i in range(len(blob)) if blob.startswith(b'    0.0v',i)]
    candidates=[blob[a:(starts[n+1] if n+1<len(starts) else len(blob))] for n,a in enumerate(starts)]
    return next((r for r in candidates if r[72:76]==b'ikip'),None)


def ensure_pikmin_squad(assets,data):
    """Append a red-Pikmin starting squad when a private stage has none.

    A fixture that boots with zero Pikmin immediately enters the engine's
    extinction flow (GAMEEND_PikminExtinction / DEMOID_Extinction), which the
    unattended test fixtures never clear. Every stage handed to overlay() gets a
    20-red squad unless it already carries an ``ikip`` generator record.
    """
    if data[:4]!=b'1.0v' or len(data)<24 or b'ikip' in data:return data
    template=_pikmin_template(assets)
    if template is None:return data
    starts=[m.start() for m in re.finditer(b'    0.0v',data)]
    if not starts or starts[0]!=24:return data
    entries=[data[s:(starts[i+1] if i+1<len(starts) else len(data))] for i,s in enumerate(starts)]
    used={struct.unpack_from('<I',r,8)[0] for r in entries}
    extra=[]
    for index in range(20):
        identity=(max(used)+1) if used else 1
        used.add(identity)
        row=bytearray(template)
        struct.pack_into('<I',row,8,identity)
        row[16:48]=b'fixture starting squad'.ljust(32,b'\0')
        x=-140.0+(index%10)*8.0;z=1820.0-(index//10)*8.0
        struct.pack_into('>6f',row,48,x,30.0,z,0.0,0.0,0.0)
        extra.append(bytes(row))
    return data[:20]+struct.pack('>I',len(entries)+len(extra))+b''.join(entries)+b''.join(extra)


def overlay(source,dest,overrides):
    """Only ancestor directories of replacements are writable; shared files never edited."""
    import _winapi
    key='dataDir/stages/chal0/default.gen'
    if key in overrides and (source/'dataDir/stages').is_dir():
        overrides=dict(overrides);overrides[key]=ensure_pikmin_squad(source,overrides[key])
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



def prototype_routes(source):
    """Add two goal approaches for this standalone layout, not to the P2 graph.

    P2 source points7/8 only have outgoing links. P1 assigns Onion/UFO goals
    to their nearest waypoint, so they cannot serve as destinations unchanged.
    Add only the two audited destination approaches from central point4;
    do not reverse the remaining source links or alter waypoint positions.
    """
    text=source.decode('ascii')
    ids=[int(v) for v in re.findall(r'\bindex\s+(\d+)',text)]
    if sorted(ids)!=list(range(9)):
        raise ValueError('Expected the nine original P2 room route points')
    links={(int(a),int(b)) for a,b in re.findall(r'\blink\s*{\s*(\d+)\s+(\d+)\s*}',text)}
    if not {(7,4),(8,4)}<=links:
        raise ValueError('Missing audited original goal approach edges')
    end=text.rfind('}')
    if end<0:raise ValueError('Missing route group end')
    extra=''.join(f' link {{ 4 {goal} }}\n' for goal in (7,8) if (4,goal) not in links)
    return (text[:end]+extra+text[end:]).encode('ascii')


def replace_embedded_routes(model,route):
    cursor=0
    while cursor+8<=len(model):
        tag,size=struct.unpack_from('>II',model,cursor)
        end=cursor+8+size
        if end>len(model):raise ValueError('Truncated MOD chunk')
        if tag==0xffff:return model[:end]+route
        cursor=end
    raise ValueError('Missing MOD EOF')


def prepare(assets,converted,output,reds=20):
    run=output.resolve()/uuid.uuid4().hex
    run.mkdir(parents=True)
    stage=(assets/'dataDir/stages/chal0.ini').read_bytes()
    stage=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/pikmin2room/room.mod',stage)
    stage=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -85.0 0.0',stage)
    empty=b'1.0v'+struct.pack('>4fI',-85,0,0,45,0)
    routes=prototype_routes((converted/'room.ini').read_bytes())
    room_model=replace_embedded_routes((converted/'room.mod').read_bytes(),routes)
    overrides={'dataDir/stages/chal0.ini':stage,'dataDir/stages/chal0/default.gen':generator(assets,reds),
      'dataDir/stages/chal0/plants.gen':empty,
      'dataDir/courses/pikmin2room/room.mod':room_model,
      'dataDir/courses/pikmin2room/room.ini':routes}
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
