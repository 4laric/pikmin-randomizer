"""Source-backed local Emergence content preparation; not a random-map generator."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assembly import transform
from experimental.pikmin2_assets import disc_files
from experimental.pikmin2_cave import CAVE, cave_definition
from experimental.pikmin2_pod import extract


def roster(floors):
    """Decode guaranteed populations; plant weights are counts, not packed tens."""
    result=[]
    for floor in floors:
        number=floor['number']; actors=[]
        for category, rows in [('enemy',floor['enemies']),('treasure',floor['treasures'])]:
            for row in rows:
                packed=row['packed_weight']; kind=row.get('placement_type',2)
                if packed<0: raise ValueError('Negative roster weight')
                count,weight=(packed,0) if kind==6 else divmod(packed,10)
                family='plant' if kind==6 else ('candypop' if row['id']=='BlackPom' else category)
                for i in range(count):
                    actors.append(dict(instance_id=f'tutorial_1:floor{number}:{family}:{row["id"]}:{i}',
                                       catalog_id=row['id'],category=family,placement_type=kind,
                                       placement=None,placement_status='unresolved_source_selection'))
                if weight: raise ValueError('Weighted optional populations require generator integration')
        result.append(dict(number=number,actors=actors,parameters=copy.deepcopy(floor['parameters'])))
    return result


def candidates(imported, floor, layout):
    """Keep every source slot and exact transform, including unresolved distributions."""
    result=[]
    for instance,(unit,turn,offset) in enumerate(layout):
        if unit not in imported['floors'][floor-1]['unit_candidates']:
            raise ValueError('Unit outside source floor pool')
        for index,slot in enumerate(imported['units'][unit]['spawn_candidates']):
            result.append(dict(slot_id=f'tutorial_1:floor{floor}:unit{instance}:slot{index}',
                               unit=unit,unit_instance=instance,source_index=index,
                               source=copy.deepcopy(slot),turn=turn,offset=list(offset),
                               position=transform(slot['position'],turn,offset),
                               angle=(slot['angle']-90*turn)%360))
    return result


def manifest(floors, imported, assemblies, treasures):
    result=dict(schema=1,cave='tutorial_1',floors=roster(floors),treasures=treasures,
                native_ready=False,layout_policy='existing engineering assembly, not retail map generation',
                limitations=['Native receiver supports one treasure; this manifest is not consumed by the current launcher.',
                             'Enemy group offsets and random slot selection are unresolved; candidates are not final actors.',
                             'Plant and exit selection remain unresolved; source transforms are never ground-projected here.'])
    for floor,layout in zip(result['floors'],assemblies,strict=True):
        floor['layout']=layout
        floor['slots']=candidates(imported,floor['number'],layout)
        # Only the final room has one unambiguous source treasure slot. Enemy
        # group positions still require the original random radial distribution.
        treasure_slots=[s for s in floor['slots'] if s['source']['type']==2]
        items=[a for a in floor['actors'] if a['category']=='treasure']
        if len(items)==len(treasure_slots)==1:
            slot=treasure_slots[0]
            items[0]['placement']=dict(slot_id=slot['slot_id'],position=slot['position'],angle=slot['angle'])
            items[0]['placement_status']='unique_source_slot'
        for actor in floor['actors']:
            if actor['category']=='treasure': actor['asset']=f'treasures/{actor["catalog_id"]}/treasure.mod'
    return result


def prepare(iso, imported, output):
    """Prepare all three source treasures without altering any playable profile."""
    output.mkdir(parents=True,exist_ok=False)
    index=disc_files(iso)
    with iso.open('rb') as stream:
        at,size=index[CAVE];stream.seek(at);raw=stream.read(size)
    if len(raw)!=size: raise ValueError('Truncated cave definition')
    floors=cave_definition(raw.decode('shift_jis'))
    source=json.loads((imported/'manifest.json').read_text())
    if floors != [{k:v for k,v in f.items() if k!='unit_candidates'} for f in source['floors']]:
        raise ValueError('Imported cave definitions differ from disc')
    layout1=[('room_north_tutorial_1_snow',0,[0,0,0]),('way2_snow',0,[0,0,510]),
             ('room_north_tutorial_1_snow',2,[0,0,1020])]
    layouts=[layout1,[('room_purple14x14_snow',0,[0,0,0])]]
    treasures={}
    for catalog_id in sorted({r['id'] for f in floors for r in f['treasures']}):
        asset=extract(iso,output/'treasures'/catalog_id,catalog_id)
        fields=asset['treasure']
        treasures[catalog_id]=dict(catalog_id=catalog_id,value=int(fields['money']),
                                  required_strength=int(fields['min']),carrier_slots=int(fields['max']),
                                  source_sha256=asset['source_sha256'],
                                  model_sha256=hashlib.sha256((output/'treasures'/catalog_id/'treasure.mod').read_bytes()).hexdigest())
    result=manifest(floors,source,layouts,treasures)
    result['source_sha256']=dict(source['source_sha256'])
    result['source_sha256'][CAVE]=hashlib.sha256(raw).hexdigest()
    (output/'content.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','imported','output'): p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); result=prepare(a.iso,a.imported,a.output)
    print(json.dumps(dict(floors=len(result['floors']),treasures=list(result['treasures']),native_ready=False)))
