"""Private original Impact Site arena: Frog/MaroFrog source visuals and two matching P1 controls.

The default arena places the two registered frogs at the audited ``z~1850``
bench, far from the original red goal/Onion at ``(-498.186, 1454.469)``. The
carry fixture needs the registered corpses produced near the Onion, because a
full ~520-unit haul stalls inside the original terrain before absorption. Passing
``near_onion=True`` reads the red goal record from the same original
``practice/default.gen`` and stages the two registered frogs about 120 units
from it. This is an engineered placement choice (like every coordinate in this
arena) recorded in ``frog-arena.json``; the original course bytes, generator
counts and unique IDs are preserved exactly as in the default variant.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import uuid
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position, validate_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_frog_install import install, plan


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def onion_position(practice):
    """Return the original Impact Site red Onion entry point from its goal record.

    The red goal record is the same byte-framed generator the engine uses; reading
    it (rather than hard-coding a coordinate) keeps the near-Onion placement bound
    to the original course and fails closed if the record framing changes.
    """
    goal=next((r for r in practice if r[16:48].rstrip(b'\0')==b'red goal'),None)
    if goal is None:raise ValueError('Original red goal record missing')
    x,y,z=struct.unpack_from('>3f',goal,48)
    if not all(math.isfinite(v) for v in (x,y,z)):raise ValueError('Original red goal position invalid')
    return (x,y,z)


def roster(assets,near_onion=False):
    source=assets/'dataDir/stages/practice/default.gen'
    header=source.read_bytes()[:24]
    practice=records(source)
    # Reuse audited one-actor Chappy framing, never its room placement.
    blob=generator(assets)
    starts=[i for i in range(len(blob)) if blob.startswith(b'    0.0v',i)]
    candidates=[blob[a:(starts[n+1] if n+1<len(starts) else len(blob))] for n,a in enumerate(starts)]
    enemy=next(r for r in candidates if r[72:76]==b'iket')
    used={struct.unpack_from('<I',r,8)[0] for r in practice}
    entries=list(practice)
    placements=[]
    if near_onion:
        ox,_,oz=onion_position(practice)
        registered=[(ox-40.,30.,oz+115.),(ox+40.,30.,oz+115.)]
    else:
        registered=[(-150.,30.,1850.),(150.,30.,1850.)]
    for identity,kind,teki,xyz in [(201001,'Frog',0,registered[0]),(201002,'MaroFrog',33,registered[1]),(201003,'P1 Frog',0,(-150.,30.,1550.)),(201004,'P1 Frow',33,(150.,30.,1550.))]:
        if identity in used:raise ValueError('Arena generator ID collision')
        used.add(identity)
        row=bytearray(enemy);struct.pack_into('<I',row,8,identity)
        row[16:48]=kind.encode('ascii').ljust(32,b'\0')
        row[80]=teki
        write_position(row,xyz)
        entries.append(bytes(row))
        placements.append(dict(generator=identity,species=kind,native_type=teki,position=list(validate_position(row,xyz)),offset=[0,0,0],source_yaw=None,source_yaw_applied=False))
    return header[:20]+struct.pack('>I',len(entries))+b''.join(entries),placements


def prepare(assets,bank,output,near_onion=False):
    assets=assets.resolve();bank=bank.resolve()
    data,actors=roster(assets,near_onion=near_onion)
    registered=[(a['generator'],a['species']) for a in actors[:2]]
    plan(bank,registered) # Validate every source byte before any output mutation.
    stage=assets/'dataDir/stages/practice.ini'
    course=assets/'dataDir/courses/practice'
    preserved={str(p.relative_to(assets)).replace('\\','/'):digest(p) for p in course.rglob('*') if p.is_file()}
    if not preserved:raise ValueError('Original Impact Site course missing')
    run=output.resolve()/uuid.uuid4().hex;run.mkdir(parents=True)
    empty=data[:20]+struct.pack('>I',0)
    overrides={'dataDir/stages/chal0.ini':stage.read_bytes(),'dataDir/stages/chal0/default.gen':data,'dataDir/courses/pikmin2room/arena-private.txt':b'P1 original stage arena\n'}
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    overlay(assets,run/'assets',overrides)
    birth=deterministic_births(run/'assets/dataDir/stages/chal0/default.gen',[a['generator'] for a in actors])
    install(bank,run,registered)
    (run/'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    for name,value in preserved.items():
        if digest(run/'assets'/name)!=value:raise ValueError('Original course changed')
    result=dict(schema=1,scene='P1 Impact Site',stage_slot='chal0',actors=actors,added_enemy_count=4,source_stage_sha256=digest(stage),preserved_course_sha256=preserved,profile_sha256=digest(bank/'frogs.json'),birth_policy=birth,command=['nectar.exe','--experimental-pikmin2-room'],near_onion=bool(near_onion),placement_choice=('Registered corpses staged ~120 units from the original red goal/Onion (near_onion) to bound the corpse carry route; engineered coordinates, terrain/physical spawn acceptance unmeasured' if near_onion else 'Engineered arena coordinates; terrain/physical spawn acceptance unmeasured'),gates={key:'untested' for key in ('native_identity','natural_AI','combat','death','delivery','reload')},limitations=['No Pod reward binding; native P1 corpse behavior retained','No source yaw applied','Source Frog/MaroFrog sampled visuals only; P1 AI, health, collision and rewards unchanged'])
    (run/'frog-arena.json').write_bytes((json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
    return run


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','bank','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--near-onion',action='store_true',help='stage the registered frogs near the original red goal/Onion')
    a=p.parse_args();print(prepare(a.assets,a.bank,a.output,near_onion=a.near_onion))
