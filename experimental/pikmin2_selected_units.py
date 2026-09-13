"""Selected cave-unit import with explicit unsupported/approximate asset status."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_cave import BASE,route_audit,safe_name,tree
from experimental.pikmin2_collision import attach_collision,decode_room,ground_height,route_ini
from experimental.pikmin2_convert import convert


def select(catalog,dependencies,cave_id):
    if catalog.get('schema')!=1 or dependencies.get('schema')!=1:raise ValueError('Unsupported catalog schema')
    caves=[c for c in catalog['caves'] if c['cave_id']==cave_id]
    deps=[c for c in dependencies['caves'] if c['cave_id']==cave_id]
    if len(caves)!=1 or len(deps)!=1:raise ValueError('Missing or ambiguous cave selection')
    expected={};floors=[]
    if len(caves[0]['floors'])!=len(deps[0]['floors']):raise ValueError('Floor dependency count differs')
    for floor,dependency in zip(caves[0]['floors'],deps[0]['floors'],strict=True):
        pool=floor['parameters']['f008']
        if pool!=dependency['unit_pool'] or (floor['first_floor'],floor['last_floor'])!=(dependency['first_floor'],dependency['last_floor']):
            raise ValueError('Floor dependency mapping differs')
        units=catalog['unit_pools'][pool]['units']
        if sorted(u['name'] for u in units)!=dependency['unit_candidates']:raise ValueError('Unit dependency set differs')
        for definition in units:
            name=safe_name(definition['name'])
            if name in expected and expected[name]!=definition:raise ValueError('Conflicting unit definitions')
            expected[name]=definition
        floors.append(dict(first_floor=floor['first_floor'],last_floor=floor['last_floor'],unit_pool=pool,unit_candidates=dependency['unit_candidates']))
    return dict(sorted(expected.items())),floors


def import_units(iso,catalog_path,dependency_path,output,cave_id='forest_1',approximate_materials=False):
    output.mkdir(parents=True,exist_ok=False)
    catalog_bytes=catalog_path.read_bytes();catalog=json.loads(catalog_bytes)
    dependencies=json.loads(dependency_path.read_bytes())
    if dependencies['catalog_sha256']!=hashlib.sha256(catalog_bytes).hexdigest():raise ValueError('Dependency catalog fingerprint differs')
    selected,floors=select(catalog,dependencies,cave_id)
    files=disc_files(iso);hashes={};units={}
    with iso.open('rb') as disc:
        def read(path):
            if path not in files:raise ValueError('Missing disc dependency: '+path)
            offset,size=files[path];disc.seek(offset);data=disc.read(size)
            if len(data)!=size:raise ValueError('Truncated disc asset')
            hashes[path]=hashlib.sha256(data).hexdigest();return data
        for path,expected in catalog['source_sha256'].items():
            if hashlib.sha256(read(path)).hexdigest()!=expected:raise ValueError('Catalog disc source changed')
        for name,definition in selected.items():
            directory=output/'units'/name
            result=dict(definition=definition,status='unsupported',assembly_ready=False)
            units[name]=result
            for folder in ('arc','texts'):
                for member,data in archive_files(read(f'{BASE}/arc/{name}/{folder}.szs')).items():
                    target=directory/folder/member;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            try:
                water=tree((directory/'texts/waterbox.txt').read_text())
                result['water']=dict(empty=water==['0',['0']],source=water)
                if not result['water']['empty']:raise ValueError('Water-volume conversion not implemented')
                room=decode_room(directory/'texts')
                route_ids={r['id'] for r in room['routes']}
                if any(d['waypoint'] not in route_ids for d in definition['doors']):raise ValueError('Door references missing waypoint')
                result['route_audit']=route_audit(room)
                result['spawn_ground_probes']=[dict(source_slot=i,source_position=s['position'],ground=ground_height(room['vertices'],room['triangles'],s['position'][0],s['position'][2])) for i,s in enumerate(room['spawns'])]
                result['collision_triangles']=len(room['triangles'])
                result['deferred_animations']=sorted(p.name for p in (directory/'arc').iterdir() if p.suffix in ('.btk','.bck','.bca','.brk','.btp'))
                try:
                    report=convert(directory/'arc/view.bmd',directory/'render.mod')
                    result['material_status']='strict_converter_supported'
                except ValueError as error:
                    result['strict_conversion_failure']=str(error)
                    if not approximate_materials:raise
                    report=convert(directory/'arc/view.bmd',directory/'render.mod',approximate_materials=True)
                    result['material_status']='explicit_approximation'
                result['render']={k:v for k,v in report.items() if k not in ('source','output')}
                (directory/'room.mod').write_bytes(attach_collision((directory/'render.mod').read_bytes(),room))
                (directory/'room.ini').write_text(route_ini(room['routes']))
                (directory/'collision.json').write_text(json.dumps(room,indent=2)+'\n')
                result['status']='converted';result['assembly_ready']=True
                result['output_sha256']={file:hashlib.sha256((directory/file).read_bytes()).hexdigest() for file in ('render.mod','room.mod','room.ini','collision.json')}
            except (ValueError,FileNotFoundError) as error:
                result['failure']=str(error)
    manifest=dict(schema=1,cave_id=cave_id,floors=floors,units=units,source_sha256=hashes,
                  catalog_sha256=hashlib.sha256(catalog_bytes).hexdigest(),dependency_sha256=hashlib.sha256(dependency_path.read_bytes()).hexdigest(),
                  approximate_materials=approximate_materials,assembled=False,native_validated=False,
                  limitations=['Candidates only; no selected topology, rotated placement or seam assembly.',
                               'Route audits are unit-local; they do not establish cross-unit reachability or actor carry paths.',
                               'Explicit approximate conversion does not reproduce original TEV or texture animation.'])
    (output/'units.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','catalog','dependencies','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cave',default='forest_1');p.add_argument('--approximate-materials',action='store_true')
    a=p.parse_args();m=import_units(a.iso,a.catalog,a.dependencies,a.output,a.cave,a.approximate_materials)
    print(json.dumps(dict(cave=m['cave_id'],units=len(m['units']),converted=sum(u['status']=='converted' for u in m['units'].values()),unsupported={k:u['failure'] for k,u in m['units'].items() if u['status']!='converted'})))
