"""Source floor4 engineering assembly and native survey, not campaign launch."""
import json
from pathlib import Path
import re

from experimental.pikmin2_beasts_floor3_assembly import build as assemble
from experimental.pikmin2_beasts_floor3_runtime import stage as prepare_stage,fixture as prepare_fixture,sha

ROOMS=('room_mid1_6_tsuchi','room_north3_1_tsuchi')
POOL='2_ABE_mid1_nor3_tsuchi.txt'
GOALS=[(0,-550),(0,-640),(0,-720),(0,-830),(10,-950),(25,-1080),
       (10,-950),(0,-830),(0,-720),(0,-640),(0,-550),(0,-425)]
ANCHORS=dict(start=(0,-425),pod=(-255,-340),ship=(255,-340))


def build(iso,catalog,units,final_package,output):
    raw=(final_package/'final-floors.json').read_bytes();report=json.loads(raw)
    catalog_raw=catalog.read_bytes();source=json.loads(catalog_raw)
    if report['policy']!='P2_BEASTS_FINAL_FLOORS_1' or report['catalog_sha256']!=sha(catalog_raw):raise ValueError('Final-floor package provenance mismatch')
    cave=[c for c in source['caves'] if c['cave_id']=='forest_1']
    if len(cave)!=1:raise ValueError('Ambiguous Beasts cave')
    floors=[f for f in cave[0]['floors'] if f['first_floor']<=4<=f['last_floor']]
    bound=[f for f in report['floors'] if f['floor']==4]
    if len(floors)!=1 or len(bound)!=1 or floors[0]!=bound[0]['source_definition'] or floors[0]['parameters']['f008']!=POOL:
        raise ValueError('Final-floor definition changed')
    for name in ROOMS:
        metadata=report['rooms'][name]
        if metadata['floor']!=4:raise ValueError('Wrong prepared room floor')
        for file in ('room.mod','room.ini','collision.json'):
            if sha((final_package/'rooms'/name/file).read_bytes())!=metadata['output_sha256'][file]:raise ValueError('Prepared room changed')
    result=assemble(iso,catalog,units,output,floor=4,room_names=ROOMS,pool=POOL,cap='item_cap_tsuchi')
    result['final_package_sha256']=sha(raw)
    result['source_definition']=floors[0]
    result['limitations'][-1]='No actors, treasures, receipts, native launch or floor4 campaign entry/descent.'
    (output/'assembly.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def stage(assets,assembly,purple,pod,output,party):
    directory=prepare_stage(assets,assembly,purple,pod,output,party,floor=4,goals=GOALS,anchor_positions=ANCHORS)
    path=directory/'survey.json';report=json.loads(path.read_bytes())
    report['limitations'][0]='Engineering party-only restore uses existing tutorial floor2 loader; no floor4 campaign entry.'
    path.write_text(json.dumps(report,indent=2)+'\n')
    return directory


def fixture(source,output):
    prepare_fixture(source,output)
    raw=output.read_text();replacement='static const float goals[12][2]={'+','.join('{'+str(x)+','+str(z)+'}' for x,z in GOALS)+'};'
    raw,count=re.subn(r'static const float goals\[12\]\[2\]=\{.*?\};',replacement,raw,flags=re.S)
    if count!=1:raise ValueError('Survey goal declaration changed')
    native_check='pc_p2_cave_floor()==3 && pc_p2_cave_is_beasts()'
    if raw.count(native_check)!=1:raise ValueError('Native profile check anchor changed')
    output.write_text(raw.replace(native_check,'pc_p2_cave_floor()==4 && pc_p2_cave_is_beasts()').replace('P2_FLOOR3','P2_FLOOR4').replace('floor3','floor4'))
    return output
