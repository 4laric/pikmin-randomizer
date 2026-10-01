"""Fresh engineering-preview receiver diagnostic; ordinary tutorial/AP gate stays open."""
import hashlib,json,re,struct
from pathlib import Path
from scripts.stage_pikmin2_tutorial_encounter import prepare as tutorial,ENEMY_UID,ONION_UID,START
from scripts.preview_pikmin2_room import records,overlay
from randomizer.purple_campaign import add_violet,bank_files

VIOLET_UID=0x50555255

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
    data=gen.read_bytes()[:24]+b''.join(rows)
    template=next(r for r in records(assets/'dataDir/stages/chal0/default.gen')
                  if r[72:80]==b'ssob\x02\x00\x00\x00')
    data=add_violet(data,template,VIOLET_UID,1)
    native_rows=list(re.finditer(rb'    0\.0v',data))
    if len(native_rows)!=23:raise ValueError('20Red/Onion/Red/Violet physical framing')
    stage=(original/'dataDir/stages/p2_tutorial.ini').read_bytes()
    empty=b'1.0v'+struct.pack('>4fI',*START,0,0)
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
                enemy_uid=ENEMY_UID,violet_uid=VIOLET_UID,violet_placement='engineering START+100x; existing Boss template',
                source_enemy_position_retained=True,source_terrain_routes_retained=True,
                source_water_file_retained=True,water_consumer_active=False,ordinary_tutorial_ap_acceptance='OPEN',
                source_overlay_sha256=sha(Path(__file__).parent/'preview_pikmin2_room.py'),
                generator_sha256=sha(original/'dataDir/stages/chal0/default.gen'),
                sidecars={p.name:sha(p) for p in run.glob('p2-*.txt')},
                converted_models={name:hashlib.sha256(value).hexdigest() for name,value in overrides.items() if name.endswith('.mod')},
                launch=['--experimental-pikmin2-room'],window='960x540 centered, runtime pending',playable_accepted=False)
    (run/'purple-kochappy-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    return run
