"""Source audit and reference conversion accounting; not a campaign adapter."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_beasts_floor2 import source_floor


def proper_slots(raw):
    blocks=re.findall(rb'\{\s*\r?\n(.*?)\{_eof\}',raw,re.S)
    candidates=[b for b in blocks if b'{ip13}' in b and b'{ip11}' in b]
    if len(candidates)!=1:raise ValueError('Ambiguous Pom proper parameter block')
    values=re.findall(rb'\{ip01\}\s+4\s+(\d+)\s',candidates[0])
    if len(values)!=1 or not 1<=int(values[0])<=50:raise ValueError('Invalid Pom conversion capacity')
    return int(values[0])


def budgets(slots,global_plus_cave_purple):
    if type(global_plus_cave_purple) is not int or global_plus_cave_purple<0:raise ValueError('Missing global population context')
    return {f'forest_1:floor2:BlackPom:{i}':slots for i in range(2)} if global_plus_cave_purple<20 else {}


def conversion_reference(before,after,events,limits):
    """Events are a proposed trusted-native witness, not inferred from population."""
    used=Counter();inputs=Counter();outputs=0;seen=set()
    for event in events:
        if set(event)!={'id','flower','input'} or event['id'] in seen:raise ValueError('Duplicate/invalid conversion witness')
        seen.add(event['id']);flower=event['flower'];color=event['input']
        if flower not in limits or color not in ('red','blue','yellow','purple'):raise ValueError('Unexpected conversion')
        if color!='purple':used[flower]+=1;inputs[color]+=1;outputs+=1
        if used[flower]>limits[flower]:raise ValueError('Flower capacity exceeded')
    start=Counter(before);end=Counter(after)
    if sum(end.values())>sum(start.values()):raise ValueError('Conversion cannot grow population')
    if any(inputs[c]>start[c] for c in inputs):raise ValueError('Conversion inputs exceed available species')
    available=start-inputs;available['purple']+=outputs
    if any(end[c]>available[c] for c in end):raise ValueError('Unwitnessed species increase')
    return dict(used=dict(used),net_purple_outputs=outputs)


def audit(iso,catalog_path):
    catalog_raw=catalog_path.read_bytes();catalog=json.loads(catalog_raw);source_floor(catalog)
    cave=next(c for c in catalog['caves'] if c['cave_id']=='forest_1')
    entry=disc_files(iso)['enemy/parm/enemyParms.szs']
    with iso.open('rb') as stream:
        stream.seek(entry[0]);raw=archive_files(stream.read(entry[1]))['pom/enemyparm.txt']
    slots=proper_slots(raw)
    rows=[]
    for floor in cave['floors'][:3]:
        p=floor['parameters']
        rows.append(dict(floor=floor['first_floor'],definition=floor['definition_index'],
                         unit_pool=p['f008'],geyser=p['f007']=='1',clogged=p['f010']=='1',
                         next_floor=floor['first_floor']+1,source_parameters=p))
    return dict(schema=1,reference_only=True,cave='forest_1',floors=rows,
        catalog_sha256=hashlib.sha256(catalog_raw).hexdigest(),pom_parameter_sha256=hashlib.sha256(raw).hexdigest(),
        pom_parameter_source='enemy/parm/enemyParms.szs:pom/enemyparm.txt',slots_per_flower=slots,
        nominal_budgets=budgets(slots,0),birth_gate='floor index<2 and global+cave Purple >=20 suppresses BlackPom',
        placement_gate='Floor2 source type8 flower candidates known; no retail generated captain/hole transform asserted',
        adapter_gate='Existing schema1 only accepts tutorial floors1/2 and exits on floor2; new profile-bound adapter required')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','catalog','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'audit.json').write_text(json.dumps(audit(a.iso,a.catalog),indent=2))
