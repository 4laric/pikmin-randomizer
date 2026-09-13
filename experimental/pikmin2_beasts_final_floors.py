"""Source-bound final Beasts rooms and cargo; no generated placement or gameplay."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from experimental.pikmin2_convert import convert
from experimental.pikmin2_pod import pellet_catalog

POOLS = {4:'2_ABE_mid1_nor3_tsuchi.txt', 5:'1_units_boss_tsuchi.txt'}
ROOMS = {4:('room_mid1_6_tsuchi','room_north3_1_tsuchi'), 5:('room_boss_1_tsuchi',)}
EXPECTED = {4:[('Chappy',1,1,'donutsichigo_s'),('BlackPom',1,8,None),('Hiba',4,1,None),('HikariKinoko',6,6,None)],
            5:[('Queen',1,1,'radar_a'),('HikariKinoko',8,6,None)]}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def row_key(row):
    return row['enemy_id'],row.get('minimum_count',row.get('target_count')),row['placement_type'],row.get('carried_treasure')


def cargo_catalog(treasures,equipment):
    if treasures.keys() & equipment.keys():raise ValueError('Ambiguous cargo identity')
    return {**{name:(row,'treasure') for name,row in treasures.items()},
            **{name:(row,'equipment') for name,row in equipment.items()}}


def source_manifest(catalog):
    caves=[c for c in catalog['caves'] if c['cave_id']=='forest_1']
    if len(caves)!=1:raise ValueError('Expected one forest_1 definition')
    floors=caves[0]['floors']
    if [(f['definition_index'],f['first_floor'],f['last_floor']) for f in floors]!=[(i-1,i,i) for i in range(1,6)]:
        raise ValueError('Expected five distinct source floors')
    result=[]
    for number,floor in enumerate(floors,1):
        p=floor['parameters']
        if p['f007']!=('1' if number==5 else '0') or p['f010']!=('1' if number==5 else '0'):
            raise ValueError('Unexpected cave exit flags')
        if number in POOLS:
            cap_rows=[c['enemy'] for c in floor['caps'] if not c['empty']]
            expected_caps=[('TamagoMushi',1,1,None),('Egg',2,1,None)] if number==4 else []
            if (p['f008']!=POOLS[number] or [row_key(r) for r in floor['enemies']]!=EXPECTED[number]
                    or len(cap_rows)!=len(floor['caps']) or [row_key(r) for r in cap_rows]!=expected_caps
                    or floor['gates'] or floor['treasures']!=([dict(treasure_id='dia_b_blue',source_weight=10,minimum_count=1,selection_weight=0)] if number==4 else [])):
                raise ValueError('Final-floor roster/pool changed')
            if any(r.get('selection_weight',0) or r.get('drop_mode',0) for r in floor['enemies']+cap_rows):
                raise ValueError('Unexpected weighted or special-drop actor')
            names=[u['name'] for u in catalog['unit_pools'][p['f008']]['units'] if u['kind']==1]
            if sorted(names)!=sorted(ROOMS[number]):raise ValueError('Final-floor room pool changed')
        actors=[];cargo=[]
        for category,rows in [('enemy',floor['enemies']),('cap',[c['enemy'] if not c['empty'] else None for c in floor['caps']])]:
            for index,row in enumerate(rows):
                identity=f'forest_1:definition{number-1}:{category}:{index}'
                actors.append(dict(definition_id=identity,source=deepcopy(row),runtime_status='not_certified_by_this_package'))
                if row and row.get('carried_treasure'):
                    cargo.append(dict(definition_id=identity+':cargo',treasure_id=row['carried_treasure'],
                        owner_definition_id=identity,delivery='enemy_carried',placement=None))
        for index,row in enumerate(floor['treasures']):
            cargo.append(dict(definition_id=f'forest_1:definition{number-1}:treasure:{index}',
                treasure_id=row['treasure_id'],owner_definition_id=None,delivery='loose',placement=None))
        result.append(dict(floor=number,source_definition=deepcopy(floor),actors=actors,cargo=cargo,
            exit=dict(destination_floor=number+1 if number<5 else None,geyser=number==5,clogged=number==5,
                      placement=None,native_supported=False),native_ready=False))
    return result


def prepare(iso,catalog_path,units,output):
    raw=catalog_path.read_bytes();catalog=json.loads(raw);floors=source_manifest(catalog)
    imported=json.loads((units/'units.json').read_bytes())
    if imported['cave_id']!='forest_1' or imported['catalog_sha256']!=sha(raw):
        raise ValueError('Unit/catalog provenance mismatch')
    sources=dict(catalog['source_sha256'])
    for name,digest in imported['source_sha256'].items():
        if name in sources and sources[name]!=digest:raise ValueError('Conflicting source provenance')
        sources[name]=digest
    index=disc_files(iso);hashes={};models={};economy={}
    with iso.open('rb') as disc:
        def read(name):
            offset,size=index[name];disc.seek(offset);data=disc.read(size)
            if len(data)!=size:raise ValueError('Truncated disc asset')
            hashes[name]=sha(data);return data
        for name,digest in sources.items():
            if sha(read(name))!=digest:raise ValueError('Disc provenance mismatch: '+name)
        config=cargo_catalog(pellet_catalog(read('user/Abe/Pellet/us/otakara_config.txt').decode('shift_jis')),
                             pellet_catalog(read('user/Abe/Pellet/us/item_config.txt').decode('shift_jis')))
        for name in sorted({c['treasure_id'] for f in floors[3:] for c in f['cargo']}):
            row,kind=config[name];value,weight,slots=[int(row[k]) for k in ('money','min','max')]
            if not 0<value<=10000 or not 1<=weight<=slots<=100:raise ValueError('Invalid cargo economy')
            economy[name]=dict(value=value,weight=weight,slots=slots,source_config=row,catalog_kind=kind,
                               equipment_effect_installed=False)
            members=archive_files(read('user/Abe/Pellet/us/'+row['archive']))
            matches=[v for k,v in members.items() if k.lower()==row['bmd'].lower()]
            if len(matches)!=1:raise ValueError('Missing or ambiguous cargo model')
            models[name]=matches[0]
    rooms={}
    for number,names in ROOMS.items():
        definitions={u['name']:u for u in catalog['unit_pools'][POOLS[number]]['units']}
        for name in names:
            record=imported['units'][name];files={}
            if record['definition']!=definitions[name] or not record['assembly_ready']:
                raise ValueError('Unsupported room: '+name)
            for filename in ('render.mod','room.mod','room.ini','collision.json'):
                data=(units/'units'/name/filename).read_bytes()
                if sha(data)!=record['output_sha256'][filename]:raise ValueError('Room hash mismatch: '+name+'/'+filename)
                files[filename]=data
            room=json.loads(files['collision.json']);probes=[]
            for slot,spawn in enumerate(room['spawns']):
                x,y,z=spawn['position'];ground=ground_height(room['vertices'],room['triangles'],x,z)
                probes.append(dict(source_slot=slot,source=spawn,ground=ground,has_floor_support=ground is not None,
                    source_y_matches_floor=ground is not None and abs(y-ground)<=.1,placement_selected=False))
            rooms[name]=dict(floor=number,source=record,spawn_ground_audit=probes,exits_capped=True,
                files={'room.mod':attach_collision(files['render.mod'],room,cap_exits=True),
                       'room.ini':route_ini(room['routes']).encode('ascii'),'collision.json':files['collision.json']})
    output.mkdir(parents=True,exist_ok=False)
    for name,data in models.items():
        directory=output/'treasures'/name;directory.mkdir(parents=True)
        source=directory/'source.bmd';target=directory/'treasure.mod';source.write_bytes(data)
        first=convert(source,target,True,bake_rigid=True)
        report=convert(source,target,True,y_offset=-first['bounds'][1],bake_rigid=True)
        report.update(source='source.bmd',output='treasure.mod')
        (directory/'treasure.json').write_text(json.dumps(report,indent=2)+'\n')
        economy[name].update(source_model_sha256=sha(data),model_sha256=sha(target.read_bytes()),conversion=report)
    for name,room in rooms.items():
        directory=output/'rooms'/name;directory.mkdir(parents=True)
        files=room.pop('files')
        for filename,data in files.items():(directory/filename).write_bytes(data)
        room['output_sha256']={f:sha(d) for f,d in files.items()}
    result=dict(schema=1,policy='P2_BEASTS_FINAL_FLOORS_1',cave='forest_1',catalog_sha256=sha(raw),source_sha256=hashes,
        floors=floors,rooms=rooms,treasure_assets=economy,native_ready=False,retail_generation=False,
        limitations=['Definition-row identities are not generated spawn or reward instance IDs.',
            'Floors1-3 are source coverage only; this package certifies no actor implementation.',
            'Floors4/5 rooms are isolated and capped; routes/spawns preserved, no selected placements or carrying proof.',
            'Carried treasure remains attached to its source owner; no loose substitution, death reward or receipt installed.',
            'Violet generation gate, Hiba, cap helpers, Queen behavior, clogged geyser and campaign resume remain unsupported here.',
            'Converted materials are approximate; no native runtime or natural-play claim.'])
    (output/'final-floors.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','catalog','units','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();prepare(args.iso,args.catalog,args.units,args.output)
    print(args.output/'final-floors.json')
