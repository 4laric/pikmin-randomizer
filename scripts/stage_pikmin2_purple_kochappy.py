"""Fresh engineering-preview receiver diagnostic; ordinary tutorial/AP gate stays open."""
import hashlib,json,re,struct,math
from pathlib import Path
from scripts.stage_pikmin2_tutorial_encounter import prepare as tutorial,ENEMY_UID,ONION_UID,START
from scripts.preview_pikmin2_room import records,overlay
from randomizer.purple_campaign import add_violet,bank_files
from experimental.pikmin2_collision import plane

VIOLET_UID=0x50555255
# Engineering starting squad only: avoid combat during ordinary startup readiness.
PREVIEW_START=(START[0]+260,START[1],START[2])
# Retain the existing engineering Violet XZ; only its prebirth Y is grounded.
VIOLET_XZ=(START[0]+300,START[2])
SPAWN_CLEARANCE=40.0

def positive_floor(room,x,z):
    """Highest containing positive-Y source face; never invent a ground plane."""
    if not all(math.isfinite(v) for v in (x,z)):raise ValueError('Nonfinite engineering spawn')
    hits=[];vertices=room['vertices']
    for index,tri in enumerate(room['triangles']):
        a,b,c=(vertices[i] for i in tri);nx,ny,nz,offset=plane(vertices,tri)
        if ny<=0:continue
        den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(den)<1e-8:continue
        u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den
        v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
        if min(u,v,1-u-v)>=-1e-6:
            y=(offset-nx*x-nz*z)/ny
            if math.isfinite(y):hits.append((y,index))
    if not hits:raise ValueError('No positive source floor beneath engineering spawn')
    return max(hits,key=lambda hit:(hit[0],-hit[1]))

def prepare(assets,bundle,identity,red_bank,purple_bank,motion,pod,output):
    run=tutorial(assets,bundle,identity,red_bank,output,5)
    original=run/'assets'
    gen=original/'dataDir/stages/p2_tutorial/default.gen'
    rows=[bytearray(r) for r in records(gen)]
    if len(rows)!=22 or sum(r[72:76]==b'ikip' for r in rows)!=20:
        raise ValueError('Current20Red plus original Onion/enemy required')
    # The engine's readID is little-endian; numeric generator framing is big-endian.
    # Distinct engineering preview inputs never rewrite the ordinary1150 source.
    struct.pack_into('<I',rows[-2],8,ONION_UID)
    struct.pack_into('<I',rows[-1],8,ENEMY_UID)
    geometry_path=bundle/'surface-geometry.json'
    geometry=json.loads(geometry_path.read_text(encoding='utf8'))
    placement=[]
    captain_floor,captain_face=positive_floor(geometry,PREVIEW_START[0],PREVIEW_START[2])
    captain_start=(PREVIEW_START[0],captain_floor+SPAWN_CLEARANCE,PREVIEW_START[2])
    # Retail Onion/enemy birth records stay intact; shift only the pre-existing
    # engineered starting20Red grid before native birth, never live actors.
    for index,row in enumerate(rows[:20]):
        x,y,z=struct.unpack_from('>3f',row,48);x+=260
        floor,face=positive_floor(geometry,x,z)
        struct.pack_into('>3f',row,48,x,floor+SPAWN_CLEARANCE,z)
        placement.append(dict(slot=index,source_face=face,source_floor=floor,birth_xyz=[x,floor+SPAWN_CLEARANCE,z]))
    header=bytearray(gen.read_bytes()[:24])
    struct.pack_into('>3f',header,4,*captain_start)
    data=bytes(header)+b''.join(rows)
    template=next(r for r in records(assets/'dataDir/stages/chal0/default.gen')
                  if r[72:80]==b'ssob\x02\x00\x00\x00')
    data=add_violet(data,template,VIOLET_UID,1)
    violet_floor,violet_face=positive_floor(geometry,*VIOLET_XZ)
    data=bytearray(data)
    violet_offset=list(re.finditer(rb'    0\.0v',data))[-1].start()
    struct.pack_into('>3f',data,violet_offset+48,VIOLET_XZ[0],violet_floor,VIOLET_XZ[1])
    data=bytes(data)
    native_rows=list(re.finditer(rb'    0\.0v',data))
    if len(native_rows)!=23:raise ValueError('20Red/Onion/Red/Violet physical framing')
    stage=(original/'dataDir/stages/p2_tutorial.ini').read_bytes()
    stage=re.sub(rb'(?m)^navi_start[^\r\n]*',('navi_start %.6f %.6f' % (PREVIEW_START[0],PREVIEW_START[2])).encode(),stage)
    empty=b'1.0v'+struct.pack('>4fI',*captain_start,0,0)
    models,sidecars=bank_files(purple_bank,motion)
    profile=sidecars['p2-purple.txt'].decode('ascii')
    if 'impact red_earthquake_v1' not in profile.splitlines():
        profile+='\nimpact red_earthquake_v1\n'
    sidecars['p2-purple.txt']=profile.encode('ascii')
    overrides={'dataDir/stages/chal0.ini':stage,'dataDir/stages/chal0/default.gen':data}
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name,empty)
    overrides.update({'dataDir/courses/pikmin2room/'+name:value for name,value in models.items()})
    # Cargo-free preview still needs the existing imported Pod anchor to enable
    # Purple presentation. No treasure actor or reward is added to this test.
    overrides['dataDir/courses/pikmin2room/pod.mod']=(pod/'pod.mod').read_bytes()
    old=run/'tutorial-base-assets';original.rename(old);overlay(old,original,overrides)
    for name,value in sidecars.items():(run/name).write_bytes(value)
    (run/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    (run/'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n',encoding='ascii')
    # Bank installation has already validated every model/profile/UID list.
    (run/'p2-kochappy-actors.txt').write_text(f'P2_KOCHAPPY_ACTORS_1 1\n{ENEMY_UID}\n',encoding='ascii')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    record=dict(schema=1,issue=1155,scope='engineering room-preview ordinary SDL receiver diagnostic only',
                starting_red=20,starting_purple=0,expected_conversion='one-for-one ordinary Violet throw/pluck; no flags injected',
                enemy_uid=ENEMY_UID,violet_uid=VIOLET_UID,violet_placement='retained engineering START+300x XZ; positive source floor Y; existing Boss template',
                original_engineering_start=START,captain_start=captain_start,starting_overlay_x_delta=260,
                engineering_floor_clearance=SPAWN_CLEARANCE,source_geometry_sha256=hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
                captain_source_face=captain_face,captain_source_floor=captain_floor,starting_body_floor_placements=placement,
                violet_source_face=violet_face,violet_source_floor=violet_floor,violet_birth_xyz=[VIOLET_XZ[0],violet_floor,VIOLET_XZ[1]],
                setup='initial native births only; no live actor relocation',
                source_enemy_position_retained=True,source_terrain_routes_retained=True,
                source_water_file_retained=True,water_consumer_active=False,ordinary_tutorial_ap_acceptance='OPEN',
                source_overlay_sha256=sha(Path(__file__).parent/'preview_pikmin2_room.py'),
                generator_sha256=sha(original/'dataDir/stages/chal0/default.gen'),
                sidecars={p.name:sha(p) for p in run.glob('p2-*.txt')},
                converted_models={name:hashlib.sha256(value).hexdigest() for name,value in overrides.items() if name.endswith('.mod')},
                launch=['--experimental-pikmin2-room'],window='960x540 centered, runtime pending',playable_accepted=False)
    (run/'purple-kochappy-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    return run
