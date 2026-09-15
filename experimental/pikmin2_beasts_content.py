"""Source floor-one cargo and explicit unsupported roster for authored Beasts rooms."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_convert import convert
from experimental.pikmin2_pod import pellet_catalog
from experimental.pikmin2_beasts_fixture import prepare as prepare_fixture


def sha(data): return hashlib.sha256(data).hexdigest()


def floor_roster(catalog):
    cave = next(c for c in catalog['caves'] if c.get('cave_id',c.get('id',c.get('cave'))) == 'forest_1')
    floors = [f for f in cave['floors'] if f['first_floor'] <= 1 <= f['last_floor']]
    if len(floors) != 1: raise ValueError('Ambiguous first floor')
    floor = floors[0]
    if floor['treasures'] != [{'treasure_id':'juji_key_fc','source_weight':10,'minimum_count':1,'selection_weight':0}]:
        raise ValueError('Unexpected floor-one cargo roster')
    expected = [('UjiB',4),('UjiA',2),('UjiA',2),('UjiA',2),('Clover',4),('Tukushi',2),('KareOoinu_s',2)]
    actual = [(r['enemy_id'],r.get('minimum_count',r.get('target_count'))) for r in floor['enemies']]
    if actual != expected or any(r.get('selection_weight',0) for r in floor['enemies']):
        raise ValueError('Unexpected floor-one source populations')
    if floor['gates'] or floor['caps']: raise ValueError('Unexpected floor-one fixture populations')
    rows = []
    for i, row in enumerate(floor['enemies']):
        rows.append(dict(definition_id=f'forest_1:definition{floor["definition_index"]}:enemy:{i}',source=row,
            runtime_status='unsupported',reason='No audited native P2 species implementation in this stage',placement=None))
    return dict(schema=1,cave='forest_1',floor=1,parameters=floor['parameters'],enemies=rows,
        treasures=floor['treasures'],gates=floor['gates'],caps=floor['caps'],
        exit=dict(has_geyser=floor['parameters']['f007'] == '1',clogged_hole=floor['parameters']['f010'] == '1',descent='Required for nonfinal floor; selected position and lifecycle unsupported'),
        retail_generation=False,complete_roster=False)


def import_content(iso, catalog_path, output):
    catalog_bytes=catalog_path.read_bytes();catalog=json.loads(catalog_bytes);result=floor_roster(catalog)
    index=disc_files(iso);hashes={}
    with iso.open('rb') as disc:
        def read(name):
            offset,size=index[name];disc.seek(offset);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated disc asset')
            hashes[name]=sha(raw);return raw
        cave_path='user/Mukki/mapunits/caveinfo/forest_1.txt'
        if sha(read(cave_path)) != catalog['source_sha256'][cave_path]:raise ValueError('Catalog/disc cave mismatch')
        config_path='user/Abe/Pellet/us/otakara_config.txt'
        selected=pellet_catalog(read(config_path).decode('shift_jis'))['juji_key_fc']
        fields=[int(selected[k]) for k in ('money','min','max')]
        if fields != [100,5,10]:raise ValueError('Unexpected source juji_key_fc economy')
        archive='user/Abe/Pellet/us/'+selected['archive']
        members=archive_files(read(archive));matches=[v for k,v in members.items() if k.lower()==selected['bmd'].lower()]
        if len(matches)!=1:raise ValueError('Ambiguous treasure model member')
        output.mkdir(parents=True,exist_ok=False)
        model=output/'source.bmd';model.write_bytes(matches[0])
        converted=convert(model,output/'treasure.mod',True,bake_rigid=True)
        converted=convert(model,output/'treasure.mod',True,y_offset=-converted['bounds'][1],bake_rigid=True)
    converted['source']='source.bmd';converted['output']='treasure.mod'
    result['cargo']=dict(catalog_id='juji_key_fc',instance_id='forest_1:floor1:treasure:juji_key_fc:0',value=100,weight=5,slots=10,
        placement_status='engineering east-room center; not selected retail spawn',model_sha256=sha((output/'treasure.mod').read_bytes()),conversion=converted)
    result['source_sha256']=hashes;result['catalog_sha256']=sha(catalog_bytes)
    (output/'content.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def stage(assets,assembly,pod,content,output):
    metadata=json.loads((content/'content.json').read_text());model=(content/'treasure.mod').read_bytes()
    if metadata['cargo']['catalog_id']!='juji_key_fc' or sha(model)!=metadata['cargo']['model_sha256']:raise ValueError('Source cargo import mismatch')
    run=prepare_fixture(assets,assembly,pod,output)
    # These files are explicit private overrides produced by prepare_fixture.
    (run/'assets/dataDir/courses/pikmin2room/treasure.mod').write_bytes(model)
    (run/'p2-pod.txt').write_text('P2_POD_1\njuji_key_fc 100 5 10\nKochappy 2\n')
    report=json.loads((run/'fixture.json').read_text());report['cargo']='Source juji_key_fc:100 Pokos,5 strength,10 slots'
    report['override_sha256']['dataDir/courses/pikmin2room/treasure.mod']=sha(model)
    report['source_content']=metadata
    report['limitations'].append('Existing second-floor automated fixture expects180 Pokos; this100-Poko stage requires general economy assertion before native automated acceptance.')
    (run/'fixture.json').write_text(json.dumps(report,indent=2)+'\n')
    return run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','catalog','output'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('assets','assembly','pod'):p.add_argument('--'+name,type=Path)
    a=p.parse_args()
    if any((a.assets,a.assembly,a.pod)) and not all((a.assets,a.assembly,a.pod)):p.error('Stage requires assets, assembly and pod together')
    imported=a.output/'import';result=import_content(a.iso,a.catalog,imported)
    print(imported,flush=True)
    if a.assets:print(stage(a.assets.resolve(),a.assembly.resolve(),a.pod.resolve(),imported,a.output/'runs'),flush=True)


if __name__=='__main__':main()
