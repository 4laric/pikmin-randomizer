"""Private original Impact Site arena: one source Red and one P1 control."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position, validate_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_kochappy_bank import install


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
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
    for identity,kind,xyz in [(186001,'Kochappy',(-150.,30.,1850.)),(186002,'P1 Chappy',(150.,30.,1550.))]:
        if identity in used:raise ValueError('Arena generator ID collision')
        used.add(identity)
        row=bytearray(enemy);struct.pack_into('<I',row,8,identity)
        row[16:48]=kind.encode('ascii').ljust(32,b'\0')
        write_position(row,xyz)
        entries.append(bytes(row))
        placements.append(dict(generator=identity,species=kind,native_family='Chappy',position=list(validate_position(row,xyz)),offset=[0,0,0],source_yaw=None,source_yaw_applied=False))
    return header[:20]+struct.pack('>I',len(entries))+b''.join(entries),placements


def prepare(assets,bank,output):
    assets=assets.resolve();bank=bank.resolve()
    data,actors=roster(assets)
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
    install(bank,run,[actors[0]['generator']])
    (run/'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name,value in preserved.items():
        if digest(run/'assets'/name)!=value:raise ValueError('Original course changed')
    result=dict(schema=1,scene='P1 Impact Site',stage_slot='chal0',actors=actors,enemy_count=2,source_stage_sha256=digest(stage),preserved_course_sha256=preserved,profile_sha256=digest(bank/'kochappy-bank.json'),birth_policy=birth,command=['nectar.exe','--experimental-pikmin2-room'],placement_choice='Engineered arena coordinates; terrain/physical spawn acceptance unmeasured',gates={key:'untested' for key in ('native_identity','natural_AI','combat','death','delivery','reload')},limitations=['No Pod reward binding; native P1 corpse behavior retained','No source yaw applied','Source Red visual and health only; proxy P1 AI'])
    (run/'arena.json').write_text(json.dumps(result,indent=2))
    return run


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','bank','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(prepare(a.assets,a.bank,a.output))
