"""Private original Impact Site Breadbug proxy/control arena."""
import hashlib,json,struct,uuid
from pathlib import Path
from scripts.preview_pikmin2_room import records,generator,overlay
from experimental.pikmin2_generator_pose import write_position,validate_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_breadbug_actor import install
IDS=(186081,186082)
POSITIONS=((-150.,30.,1850.),(150.,30.,1550.))

def prepare(assets,profile,output):
    source=assets/'dataDir/stages/practice/default.gen';data=source.read_bytes();entries=records(source)
    used={struct.unpack_from('<I',r,8)[0] for r in entries}
    if used.intersection(IDS):raise ValueError('Arena generator identity collision')
    template=generator(assets);starts=[i for i in range(len(template)) if template.startswith(b'    0.0v',i)]
    candidates=[template[a:(starts[i+1] if i+1<len(starts) else len(template))] for i,a in enumerate(starts)]
    enemy=next(r for r in candidates if r[72:76]==b'iket')
    for identity,xyz in zip(IDS,POSITIONS):
        row=bytearray(enemy);struct.pack_into('<I',row,8,identity);row[80]=8;row[16:48]=f'Breadbug {identity}'.encode().ljust(32,b'\0');write_position(row,xyz);validate_position(row,xyz);entries.append(bytes(row))
    data=data[:20]+struct.pack('>I',len(entries))+b''.join(entries)
    run=output.resolve()/uuid.uuid4().hex;run.mkdir(parents=True)
    overrides={'dataDir/stages/chal0.ini':(assets/'dataDir/stages/practice.ini').read_bytes(),'dataDir/stages/chal0/default.gen':data,'dataDir/courses/pikmin2room/private-arena.txt':b'Breadbug P1 proxy arena\n'}
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):overrides.setdefault('dataDir/stages/chal0/'+p.name,data[:20]+struct.pack('>I',0))
    overlay(assets,run/'assets',overrides);birth=deterministic_births(run/'assets/dataDir/stages/chal0/default.gen',list(IDS))
    install(profile,run,[IDS[0]]);(run/'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    preserved={}
    for path in (assets/'dataDir/courses/practice').rglob('*'):
        if path.is_file():
            rel=path.relative_to(assets);raw=path.read_bytes()
            if (run/'assets'/rel).read_bytes()!=raw:raise ValueError('Original map changed')
            preserved[str(rel)]=hashlib.sha256(raw).hexdigest()
    result=dict(scene='original P1 Impact Site',ids=IDS,positions=POSITIONS,proxy=IDS[0],control=IDS[1],birth=birth,preserved=preserved,native_validated=False)
    (run/'breadbug-arena.json').write_text(json.dumps(result,indent=2));return run
