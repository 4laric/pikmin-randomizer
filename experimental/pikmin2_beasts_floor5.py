"""Isolated source boss-room engineering survey; no boss or campaign entry."""
import json
import re
from experimental.pikmin2_assets import disc_files
from experimental.pikmin2_beasts_floor3_runtime import stage as prepare_stage,fixture as prepare_fixture,sha

ROOM='room_boss_1_tsuchi'
GOALS=[(0,340),(0,170),(0,-170),(-250,-140),(0,-170),(250,-140),
       (0,-170),(0,-455),(0,-590),(0,-455),(0,85),(0,510)]
ANCHORS=dict(start=(0,510),pod=(-150,425),ship=(150,425))


def build(iso,package,output):
    raw=(package/'final-floors.json').read_bytes();report=json.loads(raw)
    if report['policy']!='P2_BEASTS_FINAL_FLOORS_1':raise ValueError('Expected final-floor source package')
    floors=[f for f in report['floors'] if f['floor']==5]
    if len(floors)!=1:raise ValueError('Expected one source floor5')
    floor=floors[0];source=floor['source_definition']
    if (source['parameters']['f008']!='1_units_boss_tsuchi.txt'
            or source['parameters']['f007']!='1' or source['parameters']['f010']!='1'
            or [(r['enemy_id'],r.get('carried_treasure')) for r in source['enemies']]!=[('Queen','radar_a'),('HikariKinoko',None)]):
        raise ValueError('Unexpected boss-room source definition')
    metadata=report['rooms'][ROOM]
    if metadata['floor']!=5 or metadata['exits_capped'] is not True:raise ValueError('Expected capped floor5 room')
    files={}
    for name in ('room.mod','room.ini','collision.json'):
        data=(package/'rooms'/ROOM/name).read_bytes()
        if sha(data)!=metadata['output_sha256'][name]:raise ValueError('Boss-room input changed')
        files[name]=data
    index=disc_files(iso)
    with iso.open('rb') as disc:
        for name,expected in report['source_sha256'].items():
            offset,size=index[name];disc.seek(offset);data=disc.read(size)
            if len(data)!=size or sha(data)!=expected:raise ValueError('Boss-room disc provenance changed')
    output.mkdir(parents=True,exist_ok=False)
    for name,data in files.items():(output/name).write_bytes(data)
    result=dict(schema=1,policy='P2_BEASTS_FLOOR5_ASSEMBLY_1',floor=5,cave='forest_1',
        layout_kind='single_isolated_capped_source_room',room=ROOM,source_definition=source,
        source_package_sha256=sha(raw),source_sha256=report['source_sha256'],
        output_sha256={name:sha(data) for name,data in files.items()},
        native_ready=False,campaign_entry=False,
        limitations=['Queen, plants, radar equipment and clogged geyser are omitted.',
            'No boss combat, carry-route certification, receipt, return or campaign floor5 entry.',
            'Single source room with original routes/spawns; no retail generation claim.'])
    (output/'assembly.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def stage(assets,assembly,purple,pod,output,party):
    directory=prepare_stage(assets,assembly,purple,pod,output,party,floor=5,goals=GOALS,anchor_positions=ANCHORS)
    path=directory/'survey.json';report=json.loads(path.read_bytes())
    report['limitations']=['Engineering party-only tutorial floor2 restoration; no floor5 campaign entry.',
        'Captain walks through the empty boss room; no Queen, plants, radar, geyser, cargo or receipts.',
        'No natural gameplay, individual squad traversal or carrying certification.']
    path.write_text(json.dumps(report,indent=2)+'\n')
    return directory


def fixture(source,output):
    prepare_fixture(source,output)
    raw=output.read_text();replacement='static const float goals[12][2]={'+','.join('{'+str(x)+','+str(z)+'}' for x,z in GOALS)+'};'
    raw,count=re.subn(r'static const float goals\[12\]\[2\]=\{.*?\};',replacement,raw,flags=re.S)
    if count!=1:raise ValueError('Survey goal declaration changed')
    output.write_text(raw.replace('P2_FLOOR3','P2_FLOOR5').replace('floor3','floor5'))
    return output
